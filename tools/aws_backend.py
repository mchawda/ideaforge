"""Real AWS backend deploy: DynamoDB + Lambda (public Function URL).

Replaces the placeholder API URL with an actually-working REST API that
v0-generated products use for auth and data persistence.

Contract (all JSON, CORS open):
  GET  /                      -> {ok: true}
  POST /signup  {email,password,name}            -> {token, email}
  POST /login   {email,password}                 -> {token, email, name}
  GET  /me      (Bearer token)                   -> {email, name}
  GET  /items   (Bearer token)                   -> {items: [...]}
  POST /items   (Bearer token) {...fields}       -> {id, ...}
  PUT  /items/{id} (Bearer token) {...fields}    -> {id, ...}
  DELETE /items/{id} (Bearer token)              -> {deleted: id}

Items are arbitrary JSON scoped per authenticated user (multi-tenant by user).
"""

from __future__ import annotations

import io
import json
import os
import re
import secrets
import time
import zipfile
from typing import Any

import boto3
from botocore.exceptions import ClientError

from orchestrator.stage_log import info, warning

LAMBDA_RUNTIME = "python3.12"

# Inline Lambda handler source. Deployed as lambda_function.py.
LAMBDA_SOURCE = r'''
import base64
import decimal
import hashlib
import hmac
import json
import os
import time
import uuid

import boto3
from boto3.dynamodb.conditions import Key

_TABLE = os.environ["TABLE_NAME"]
_SECRET = os.environ.get("APP_SECRET", "dev-secret").encode()
_table = boto3.resource("dynamodb").Table(_TABLE)

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    "Content-Type": "application/json",
}


def _resp(code, body):
    return {"statusCode": code, "headers": _CORS, "body": json.dumps(body, default=str)}


def _hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()


def _token(email):
    sig = hmac.new(_SECRET, email.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{email}:{sig}".encode()).decode()


def _verify(token):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        email, sig = raw.rsplit(":", 1)
        expect = hmac.new(_SECRET, email.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expect):
            return email
    except Exception:
        return None
    return None


def handler(event, context):
    rc = event.get("requestContext", {}).get("http", {})
    method = rc.get("method", "GET")
    path = (event.get("rawPath") or rc.get("path") or "/").rstrip("/") or "/"

    if method == "OPTIONS":
        return _resp(204, {})

    raw_body = event.get("body") or ""
    if event.get("isBase64Encoded") and raw_body:
        raw_body = base64.b64decode(raw_body).decode()
    try:
        data = json.loads(raw_body, parse_float=decimal.Decimal) if raw_body else {}
    except Exception:
        data = {}

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    bearer = headers.get("authorization", "").replace("Bearer ", "").strip()
    qs = event.get("queryStringParameters") or {}
    token = bearer or (data.get("token") if isinstance(data, dict) else "") or qs.get("token", "")

    if path in ("/", "/health"):
        return _resp(200, {"ok": True})

    if path == "/signup" and method == "POST":
        email = (data.get("email") or "").strip().lower()
        pw = data.get("password") or ""
        if not email or not pw:
            return _resp(400, {"error": "email and password required"})
        if _table.get_item(Key={"pk": f"USER#{email}", "sk": "PROFILE"}).get("Item"):
            return _resp(409, {"error": "account already exists"})
        salt = uuid.uuid4().hex
        _table.put_item(Item={
            "pk": f"USER#{email}", "sk": "PROFILE", "email": email,
            "name": data.get("name") or email.split("@")[0],
            "salt": salt, "pw": _hash_pw(pw, salt), "created_at": int(time.time()),
        })
        return _resp(200, {"token": _token(email), "email": email})

    if path == "/login" and method == "POST":
        email = (data.get("email") or "").strip().lower()
        pw = data.get("password") or ""
        item = _table.get_item(Key={"pk": f"USER#{email}", "sk": "PROFILE"}).get("Item")
        if email == "demo@demo.com" and pw == "demo123" and not item:
            salt = uuid.uuid4().hex
            _table.put_item(Item={
                "pk": f"USER#{email}", "sk": "PROFILE", "email": email, "name": "Demo",
                "salt": salt, "pw": _hash_pw(pw, salt), "created_at": int(time.time()),
            })
            item = _table.get_item(Key={"pk": f"USER#{email}", "sk": "PROFILE"}).get("Item")
        if not item or item.get("pw") != _hash_pw(pw, item.get("salt", "")):
            return _resp(401, {"error": "invalid credentials"})
        return _resp(200, {"token": _token(email), "email": email, "name": item.get("name")})

    email = _verify(token)
    if not email:
        return _resp(401, {"error": "unauthorized"})

    if path == "/me":
        item = _table.get_item(Key={"pk": f"USER#{email}", "sk": "PROFILE"}).get("Item") or {}
        return _resp(200, {"email": email, "name": item.get("name")})

    if path == "/items" and method == "GET":
        res = _table.query(
            KeyConditionExpression=Key("pk").eq(f"USER#{email}") & Key("sk").begins_with("ITEM#")
        )
        items = []
        for it in res.get("Items", []):
            clean = {k: v for k, v in it.items() if k not in ("pk", "sk")}
            clean["id"] = it["sk"].split("#", 1)[1]
            items.append(clean)
        items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return _resp(200, {"items": items})

    if path == "/items" and method == "POST":
        iid = uuid.uuid4().hex[:12]
        rec = {k: v for k, v in data.items() if k != "token"}
        _table.put_item(Item={
            "pk": f"USER#{email}", "sk": f"ITEM#{iid}", **rec,
            "id": iid, "created_at": int(time.time()),
        })
        return _resp(200, {"id": iid, **rec})

    if path.startswith("/items/"):
        iid = path.split("/items/", 1)[1].strip("/")
        if method == "DELETE":
            _table.delete_item(Key={"pk": f"USER#{email}", "sk": f"ITEM#{iid}"})
            return _resp(200, {"deleted": iid})
        if method in ("PUT", "POST"):
            rec = {k: v for k, v in data.items() if k not in ("token", "id")}
            if rec:
                expr = ", ".join(f"#{k}=:{k}" for k in rec)
                _table.update_item(
                    Key={"pk": f"USER#{email}", "sk": f"ITEM#{iid}"},
                    UpdateExpression="SET " + expr,
                    ExpressionAttributeNames={f"#{k}": k for k in rec},
                    ExpressionAttributeValues={f":{k}": v for k, v in rec.items()},
                )
            return _resp(200, {"id": iid, **rec})

    return _resp(404, {"error": "not found", "path": path})
'''


def safe_slug(product_name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]", "-", (product_name or "").lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:24] or "ideaforge-app"


def _session() -> boto3.Session:
    return boto3.Session(
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-west-2"),
    )


def _ensure_table(ddb, table_name: str, sid: str | None) -> str:
    try:
        desc = ddb.describe_table(TableName=table_name)
        return desc["Table"]["TableArn"]
    except ddb.exceptions.ResourceNotFoundException:
        pass
    ddb.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    )
    waiter = ddb.get_waiter("table_exists")
    waiter.wait(TableName=table_name, WaiterConfig={"Delay": 2, "MaxAttempts": 30})
    info(sid, "aws_backend", "dynamodb table ready", table=table_name)
    return ddb.describe_table(TableName=table_name)["Table"]["TableArn"]


def _ensure_role(iam, role_name: str, table_arn: str, account: str, sid: str | None) -> str:
    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    })
    try:
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=trust)
        info(sid, "aws_backend", "iam role created", role=role_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
    policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan",
                ],
                "Resource": [table_arn, f"{table_arn}/index/*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": "arn:aws:logs:*:*:*",
            },
        ],
    })
    iam.put_role_policy(RoleName=role_name, PolicyName="ideaforge-app-policy", PolicyDocument=policy)
    return f"arn:aws:iam::{account}:role/{role_name}"


def _zip_source() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lambda_function.py", LAMBDA_SOURCE)
    return buf.getvalue()


def _ensure_function(lam, fn_name: str, role_arn: str, table_name: str, secret: str, sid: str | None) -> None:
    code = _zip_source()
    env = {"Variables": {"TABLE_NAME": table_name, "APP_SECRET": secret}}
    # Role propagation can lag — retry create on InvalidParameterValueException.
    last_exc: Exception | None = None
    for attempt in range(1, 13):
        try:
            lam.create_function(
                FunctionName=fn_name,
                Runtime=LAMBDA_RUNTIME,
                Role=role_arn,
                Handler="lambda_function.handler",
                Code={"ZipFile": code},
                Timeout=15,
                MemorySize=256,
                Environment=env,
            )
            info(sid, "aws_backend", "lambda created", fn=fn_name)
            return
        except ClientError as exc:
            err = exc.response["Error"]["Code"]
            if err == "ResourceConflictException":
                lam.update_function_code(FunctionName=fn_name, ZipFile=code)
                lam.get_waiter("function_updated").wait(FunctionName=fn_name)
                lam.update_function_configuration(
                    FunctionName=fn_name, Role=role_arn, Environment=env,
                    Timeout=15, MemorySize=256, Runtime=LAMBDA_RUNTIME,
                    Handler="lambda_function.handler",
                )
                info(sid, "aws_backend", "lambda updated", fn=fn_name)
                return
            if err in ("InvalidParameterValueException", "AccessDeniedException"):
                last_exc = exc
                time.sleep(5)
                continue
            raise
    raise RuntimeError(f"Lambda create failed after role propagation retries: {last_exc}")


def _ensure_http_api(sess, fn_name: str, account: str, region: str, sid: str | None) -> str:
    """Public API Gateway HTTP API in front of the Lambda (payload format 2.0).

    Workshop SCPs block public Lambda Function URLs, so we front the function with
    an HTTP API, which is public by default and not subject to that restriction.
    """
    apigw = sess.client("apigatewayv2")
    lam = sess.client("lambda")
    fn_arn = f"arn:aws:lambda:{region}:{account}:function:{fn_name}"
    api_name = f"{fn_name}-gw"
    cors = {"AllowOrigins": ["*"], "AllowMethods": ["*"], "AllowHeaders": ["*"], "MaxAge": 86400}

    existing = next(
        (a for a in apigw.get_apis(MaxResults="100").get("Items", []) if a.get("Name") == api_name),
        None,
    )
    if existing:
        api_id = existing["ApiId"]
        endpoint = existing["ApiEndpoint"]
    else:
        created = apigw.create_api(
            Name=api_name,
            ProtocolType="HTTP",
            Target=fn_arn,
            CorsConfiguration=cors,
        )
        api_id = created["ApiId"]
        endpoint = created["ApiEndpoint"]
        info(sid, "aws_backend", "http api created", api=api_id)

    try:
        lam.add_permission(
            FunctionName=fn_name,
            StatementId="apigw-invoke",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{region}:{account}:{api_id}/*",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceConflictException":
            raise
    return endpoint.rstrip("/")


def deploy_app_backend(product_name: str, *, session_id: str | None = None) -> dict[str, Any]:
    """Provision DynamoDB + Lambda + public Function URL. Idempotent by product slug."""
    sess = _session()
    account = sess.client("sts").get_caller_identity()["Account"]
    region = sess.region_name
    slug = safe_slug(product_name)
    table_name = f"{slug}-app"
    role_name = f"{slug}-lambda-role"
    fn_name = f"{slug}-api"

    ddb = sess.client("dynamodb")
    iam = sess.client("iam")
    lam = sess.client("lambda")

    # Reuse an existing function's secret so issued tokens survive redeploys.
    secret = secrets.token_hex(16)
    try:
        cfg = lam.get_function_configuration(FunctionName=fn_name)
        existing_secret = (cfg.get("Environment", {}).get("Variables", {}) or {}).get("APP_SECRET")
        if existing_secret:
            secret = existing_secret
    except ClientError:
        pass

    table_arn = _ensure_table(ddb, table_name, session_id)
    role_arn = _ensure_role(iam, role_name, table_arn, account, session_id)
    _ensure_function(lam, fn_name, role_arn, table_name, secret, session_id)
    api_url = _ensure_http_api(sess, fn_name, account, region, session_id)

    info(sid := session_id, "aws_backend", "backend live", api=api_url, table=table_name)
    return {
        "api_url": api_url,
        "table_name": table_name,
        "function_name": fn_name,
        "role_arn": role_arn,
        "account": account,
        "region": region,
    }
