# IdeaForge — Complete Build Prompt
## SuperAI NEXT Hackathon 2026

> **Stack:** Python · FastAPI · AWS Lambda · DynamoDB · CDK · Vercel AI Gateway · Vercel v0 · Exa · Stripe · LangGraph  
> **Pattern:** Supervisor → Specialist Agents → Audit Trail  
> **Time budget:** 36 hours solo

---

## 0. The Pitch (One Line)

> **"IdeaBrowser shows you what to build. Ideaforge Agent builds it."**

IdeaBrowser is a curated database of pre-researched business ideas — each with market sizing, competitor analysis, and execution plans. Founder Agent is the action layer on top: paste an IdeaBrowser URL (or type any idea), and get a live, deployed, monetised SaaS in ~6 minutes.

**Demo flow on stage:**
1. Open IdeaBrowser → browse ideas → pick one
2. Paste the URL into Founder Agent → click **Build This**
3. Agent imports the validated research, makes product decisions, shows strategy brief
4. Human approves → agent builds, deploys on AWS, sets up Stripe
5. Live URL appears. Stripe checkout works. Decision brief printed.

This is the story. Everything else serves this moment.

---

## 1. Project Overview

**Founder Agent** takes a validated idea from IdeaBrowser (or a raw domain idea) and autonomously:

1. Researches the market using Exa (competitors, pricing, pain points, demand signals)
2. Decides the specific niche, product, ICP, and pricing based on evidence
3. Presents a strategy brief with sourced reasoning → human approves
4. Generates a landing page + UI via Vercel v0
5. Deploys backend infrastructure on AWS (Lambda + DynamoDB + API Gateway) via CDK
6. Creates Stripe products, pricing tiers, and embeds checkout
7. Returns a live URL with a working, monetised SaaS in ~5–8 minutes
8. Produces a full audit trail of every decision made, with sources

**Pitch differentiator:** Every decision is logged, sourced, and explainable. This is not a UI generator — it is an autonomous co-founder with a governance layer.

---

## 2. IdeaBrowser Integration

### Why no API is needed

IdeaBrowser is client-rendered (no public API). We handle this three ways:

1. **Exa fetch** — Exa renders JavaScript pages and returns clean structured text. `exa.get_contents([url])` on an IdeaBrowser idea page returns the full idea, market research, competitor analysis, and execution plan as readable text.
2. **Fallback: direct httpx** — If Exa fails, fetch the raw page and extract via LLM parsing.
3. **Manual paste** — User can paste the idea text directly. UI has a "Paste idea text" toggle as fallback.

### IdeaBrowser Importer Tool

```python
# tools/ideabrowser_tools.py
from exa_py import Exa
import os
import httpx
from anthropic import Anthropic

exa = Exa(api_key=os.environ["EXA_API_KEY"])
claude = Anthropic()

def import_idea_from_url(url: str) -> dict:
    """
    Fetch an IdeaBrowser idea page and extract structured idea data.
    Uses Exa for JS-rendered content, falls back to LLM parsing.
    """
    # Step 1: Fetch via Exa (renders JS)
    try:
        result = exa.get_contents([url], text={"max_characters": 5000})
        raw_text = result.results[0].text if result.results else ""
    except Exception:
        # Step 2: Fallback to httpx
        resp = httpx.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        raw_text = resp.text[:5000]

    if not raw_text.strip():
        raise ValueError("Could not fetch IdeaBrowser page. Use manual paste instead.")

    # Step 3: Extract structured data via LLM
    extraction_prompt = f"""
    Extract structured idea data from this IdeaBrowser page content.
    Return JSON only, no explanation.

    Content:
    {raw_text}

    Extract:
    {{
        "product_name": "...",
        "description": "...",
        "problem": "...",
        "why_now": "...",
        "market_size": "...",
        "market_gap": "...",
        "main_competitor": "...",
        "target_customer": "...",
        "execution_hints": ["...", "..."],
        "category": "...",
        "source_url": "{url}"
    }}
    """
    response = claude.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1000,
        messages=[{"role": "user", "content": extraction_prompt}]
    )

    import json
    return json.loads(response.content[0].text)


def search_ideabrowser(query: str, num_results: int = 5) -> list[dict]:
    """
    Use Exa to search IdeaBrowser for ideas matching a domain/keyword.
    Useful for the 'browse' experience in the UI.
    """
    results = exa.search_and_contents(
        f"site:ideabrowser.com {query}",
        num_results=num_results,
        text={"max_characters": 2000},
    )
    return [
        {"title": r.title, "url": r.url, "snippet": r.text}
        for r in results.results
    ]
```

### How it plugs into the agent pipeline

When a user provides an IdeaBrowser URL, the pipeline changes slightly:

```
IdeaBrowser URL provided?
    YES → IdeaBrowser Importer → pre-populate state with validated research
          → Strategy Agent (uses imported data, skips raw Exa research)
    NO  → Research Agent (full Exa market research from scratch)
          → Strategy Agent
```

The Strategy Agent system prompt gets an additional instruction when IdeaBrowser data is present:

```python
STRATEGY_AGENT_IDEABROWSER_ADDENDUM = """
You have been provided with pre-validated market research from IdeaBrowser.
Use this as your primary source of market intelligence.
You may supplement with additional Exa searches for pricing data or recent signals,
but the IdeaBrowser analysis is your foundation.
Cite IdeaBrowser as a source in your rationale.
"""
```

### UI: "Build This" button

The Founder Agent frontend (generated by v0) has two input modes:

```
┌─────────────────────────────────────────────────────┐
│  🚀 Founder Agent                                   │
│                                                     │
│  ○ Paste IdeaBrowser URL                           │
│    [ https://ideabrowser.com/ideas/... ] [Import]  │
│                                                     │
│  ○ Describe your own idea                          │
│    [ I want to build something for... ]            │
│                                                     │
│                          [ Build This → ]          │
└─────────────────────────────────────────────────────┘
```

Add this to your v0 prompt when generating the UI.

---

## 3. Repository Structure

```
founder-agent/
├── orchestrator/
│   ├── main.py                  # FastAPI entry point
│   ├── graph.py                 # LangGraph orchestration
│   ├── state.py                 # Shared agent state schema
│   └── checkpoint.py            # Human-in-the-loop checkpoint
├── agents/
│   ├── research_agent.py        # Exa-powered market research
│   ├── strategy_agent.py        # Product decision making
│   ├── builder_agent.py         # Vercel v0 UI generation
│   ├── infra_agent.py           # AWS CDK deployment
│   ├── monetization_agent.py    # Stripe setup
│   └── audit_agent.py           # Decision logging + brief generation
├── tools/
│   ├── exa_tools.py             # Exa API wrappers
│   ├── v0_tools.py              # Vercel v0 API wrappers
│   ├── vercel_tools.py          # Vercel deployment API
│   ├── stripe_tools.py          # Stripe API wrappers
│   └── cdk_tools.py             # CDK deploy trigger
├── infra/
│   ├── app.py                   # CDK app entry
│   └── saas_stack.py            # Reusable SaaS stack template
├── frontend/
│   └── dashboard/               # Vercel-deployed control panel (v0 generated)
├── .env.example
├── requirements.txt
└── README.md
```

---

## 3. Shared State Schema

```python
# state.py
from typing import TypedDict, Optional, List
from datetime import datetime

class AgentState(TypedDict):
    # Input
    user_input: str                      # Raw idea from user
    session_id: str

    # Research outputs
    market_research: Optional[dict]      # Raw Exa results
    competitors: Optional[List[dict]]    # Parsed competitors
    pain_points: Optional[List[str]]     # Extracted pain points
    demand_signals: Optional[List[str]]  # Reddit/PH/HN signals

    # Strategy outputs
    product_name: Optional[str]
    niche: Optional[str]
    icp: Optional[str]                   # Ideal customer profile
    features: Optional[List[str]]        # MVP feature list
    pricing_model: Optional[str]         # e.g. "freemium", "flat", "usage"
    price_points: Optional[List[dict]]   # e.g. [{"name": "Starter", "price": 9}]
    strategy_rationale: Optional[str]    # Sourced explanation

    # Human checkpoint
    human_approved: Optional[bool]
    human_feedback: Optional[str]

    # Build outputs
    v0_prompt: Optional[str]
    generated_ui_code: Optional[str]
    vercel_project_id: Optional[str]
    vercel_deployment_url: Optional[str]

    # Infra outputs
    aws_stack_name: Optional[str]
    aws_api_url: Optional[str]
    aws_table_name: Optional[str]

    # Monetization outputs
    stripe_product_id: Optional[str]
    stripe_price_ids: Optional[List[str]]
    stripe_checkout_url: Optional[str]
    stripe_payment_link: Optional[str]

    # Audit
    audit_log: List[dict]                # [{agent, decision, rationale, sources, timestamp}]
    final_brief: Optional[str]           # Human-readable decision brief
    final_url: Optional[str]             # The live product URL

    # Control
    error: Optional[str]
    retry_count: int
```

---

## 4. Agent System Prompts

### 4.1 Research Agent

```python
RESEARCH_AGENT_SYSTEM_PROMPT = """
You are a market research specialist agent. Your job is to investigate a business domain
and return structured intelligence that will be used to make product decisions.

You have access to the following tools:
- exa_search(query, num_results): Search the live web for structured content
- exa_find_similar(url): Find pages similar to a given competitor URL

Your research process:
1. Search for existing products and competitors in the domain
2. Search for pain points (use queries like "reddit {domain} frustrating" or "{domain} problems")
3. Search for pricing intelligence ("best {domain} tools pricing 2025")
4. Search for demand signals (Product Hunt launches, HN "Show HN", indie hacker posts)
5. Search for underserved niches ("too expensive", "no good tool for", "wish there was")

For each search, extract:
- Competitor names, pricing, and weaknesses
- Verbatim user pain points (quotes preferred)
- Market gaps or underserved segments
- Price sensitivity signals

Return your findings as structured JSON. Be specific — vague research loses. Every claim
must have a source URL.

Output format:
{
  "competitors": [{"name": ..., "url": ..., "pricing": ..., "weaknesses": [...]}],
  "pain_points": [{"quote": ..., "source": ..., "frequency": "high/medium/low"}],
  "demand_signals": [{"signal": ..., "source": ..., "date": ...}],
  "gaps": [{"gap": ..., "evidence": ..., "source": ...}],
  "price_range": {"low": ..., "high": ..., "sweet_spot": ..., "rationale": ...}
}
"""
```

### 4.2 Strategy Agent

```python
STRATEGY_AGENT_SYSTEM_PROMPT = """
You are a product strategy agent. You receive structured market research and make
decisive, evidence-based product decisions. You do not hedge — you commit to a specific
direction backed by evidence.

Your job is to decide:
1. The specific niche within the domain (be narrow and specific, not broad)
2. The product name (memorable, domain-available style)
3. The ideal customer profile (one sentence, specific)
4. The MVP feature set (3–5 features maximum — ruthlessly prioritise)
5. The pricing model and exact price points
6. The unique positioning statement (one sentence vs competitors)

Rules:
- Every decision must cite evidence from the research
- Prefer niches with clear pain, weak competitors, and willingness to pay
- Pricing should be below the market average to undercut, or premium if clearly differentiated
- MVP features must be achievable in a 36-hour hackathon backend
- Product name must be 1–2 words, punchy, and web-friendly

Output format:
{
  "product_name": "...",
  "niche": "...",
  "icp": "...",
  "positioning": "...",
  "features": ["...", "...", "..."],
  "pricing_model": "...",
  "price_points": [
    {"tier": "Free", "price": 0, "features": [...]},
    {"tier": "Pro", "price": 19, "features": [...]}
  ],
  "rationale": "Full paragraph explaining every decision with evidence citations",
  "sources": ["url1", "url2"]
}

After you produce this output, it will be shown to a human for approval before building begins.
"""
```

### 4.3 Builder Agent

```python
BUILDER_AGENT_SYSTEM_PROMPT = """
You are a frontend builder agent. You generate optimised prompts for the Vercel v0 API
to produce production-quality landing pages and SaaS UIs.

You receive the product strategy (name, niche, ICP, features, pricing) and produce:
1. A v0 prompt that generates a complete landing page
2. A v0 prompt that generates the app dashboard (post-signup)

v0 prompt guidelines:
- Be extremely specific about layout, sections, and copy
- Include the product name, tagline, and exact pricing in the prompt
- Specify: hero section, features section, pricing table, CTA, footer
- Ask for Tailwind CSS, shadcn/ui components, dark/light mode support
- Request that Stripe checkout buttons link to {{STRIPE_CHECKOUT_URL}} as a placeholder
- Request that the signup CTA links to /signup

Landing page v0 prompt template:
"Build a modern SaaS landing page for [PRODUCT_NAME], a [POSITIONING].
Target customer: [ICP].
Sections required:
- Hero: headline '[HEADLINE]', subheadline '[SUBHEADLINE]', primary CTA 'Start Free'
- Features: 3 feature cards with icons for [FEATURE_1], [FEATURE_2], [FEATURE_3]
- Pricing: [PRICING_TABLE with tiers and prices]
- Social proof: 3 placeholder testimonials from [ICP personas]
- Footer with logo, links
Use Tailwind CSS and shadcn/ui. Dark mode preferred. Make it conversion-optimised.
Replace all Stripe checkout buttons with href='{{STRIPE_CHECKOUT_URL}}'.
Export as a single Next.js page component."

After generating UI code from v0, validate it compiles and return the raw code.
"""
```

### 4.4 Infra Agent

```python
INFRA_AGENT_SYSTEM_PROMPT = """
You are an AWS infrastructure agent. You deploy a standardised SaaS backend stack
using a pre-built CDK template with configurable parameters.

You receive:
- product_name: used as the stack name prefix
- table_attributes: DynamoDB schema for the product
- api_routes: list of Lambda endpoints needed

Your job:
1. Parameterise the CDK stack template with the product details
2. Trigger CDK deploy via subprocess
3. Wait for and parse the CloudFormation outputs
4. Return the API Gateway URL and DynamoDB table ARN

The CDK stack you deploy always includes:
- AWS Lambda (Python 3.12, 512MB, 30s timeout) for API handlers
- AWS API Gateway (HTTP API) fronting the Lambda
- AWS DynamoDB (on-demand, single-table design) for data persistence
- AWS SSM Parameter Store for storing Stripe keys and config
- AWS CloudWatch for logging and monitoring
- IAM roles with least-privilege policies

You must use the provisioned AWS sandbox account credentials from environment variables.
Never create resources outside us-east-1 unless explicitly instructed.

Report every AWS resource created in the audit log with its ARN.

On failure: capture the CloudFormation error, log it, and report the specific failed resource.
"""
```

### 4.5 Monetization Agent

```python
MONETIZATION_AGENT_SYSTEM_PROMPT = """
You are a monetization agent. You configure Stripe to monetise the product based on
the approved pricing strategy.

You receive the pricing tiers (name, price, features) and:
1. Create a Stripe Product with the product name and description
2. Create Stripe Prices for each paid tier (recurring, monthly)
3. Create a Stripe Payment Link for the primary paid tier
4. Create a Stripe Checkout Session URL for embedding in the UI
5. Store all Stripe IDs in AWS SSM Parameter Store (via infra agent outputs)

For free tiers: do not create a Stripe price — just note it in the audit log.

Return:
{
  "stripe_product_id": "prod_...",
  "prices": [
    {"tier": "Pro", "price_id": "price_...", "payment_link": "https://buy.stripe.com/..."}
  ],
  "checkout_session_url": "https://checkout.stripe.com/...",
  "dashboard_link": "https://dashboard.stripe.com/products/prod_..."
}

After creating Stripe resources, trigger the builder agent to replace
{{STRIPE_CHECKOUT_URL}} in the generated UI code with the real checkout URL.
"""
```

### 4.6 Audit Agent

```python
AUDIT_AGENT_SYSTEM_PROMPT = """
You are the audit and governance agent. You run after every other agent completes
and produce two outputs:

1. A structured audit log entry for the step just completed:
{
  "timestamp": "ISO8601",
  "agent": "research|strategy|builder|infra|monetization",
  "decision": "One-sentence summary of what was decided",
  "rationale": "Why this decision was made",
  "sources": ["url1", "url2"],
  "alternatives_considered": ["option A was rejected because...", "option B..."],
  "confidence": "high|medium|low",
  "human_reviewed": true/false
}

2. After all agents complete, a final Decision Brief (markdown):
- Executive summary (3 sentences)
- Market opportunity (from research)
- Product decision (what was built and why)
- Pricing rationale (with competitor benchmarks)
- Technical architecture (AWS resources deployed)
- Revenue model (Stripe configuration)
- Risks and assumptions
- Live URL and next steps

The Decision Brief is the governance artifact — it proves the agent made defensible,
evidence-based decisions. It is included in the final output alongside the live URL.
"""
```

### 4.7 Orchestrator (Supervisor)

```python
ORCHESTRATOR_SYSTEM_PROMPT = """
You are the Founder Agent orchestrator. You coordinate a team of specialist agents
to autonomously launch a SaaS product from a single idea.

Your pipeline:
1. RESEARCH → hand off to Research Agent with the user's domain idea
2. STRATEGY → hand off research results to Strategy Agent
3. CHECKPOINT → present strategy brief to human, wait for approval
   - If rejected with feedback: loop back to Strategy Agent with feedback
   - If approved: continue
4. BUILD (parallel where possible):
   a. Builder Agent → generate and deploy UI
   b. Infra Agent → deploy AWS backend
5. MONETIZE → Monetization Agent (requires infra outputs for SSM storage)
6. INTEGRATE → replace placeholder URLs in UI with real Stripe/API URLs, redeploy
7. AUDIT → Audit Agent produces final brief
8. COMPLETE → return final URL + decision brief to user

Failure handling:
- If any agent fails: log the error, attempt one retry with adjusted parameters
- If retry fails: skip the step, note it in the audit log, continue with degraded output
- Never block the pipeline on a non-critical failure
- Always produce a final URL even if some components failed

You maintain state across all agents using the shared AgentState object.
Update the audit_log after every agent completes.
"""
```

---

## 5. LangGraph Orchestration

```python
# graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from state import AgentState
from agents.research_agent import run_research
from agents.strategy_agent import run_strategy
from agents.builder_agent import run_builder
from agents.infra_agent import run_infra
from agents.monetization_agent import run_monetization
from agents.audit_agent import run_audit
from checkpoint import human_approval_node

def should_retry_strategy(state: AgentState) -> str:
    if state.get("human_approved") is False and state.get("retry_count", 0) < 2:
        return "strategy"
    elif state.get("human_approved") is False:
        return END  # Give up after 2 retries
    return "build"

def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("research", run_research)
    graph.add_node("strategy", run_strategy)
    graph.add_node("human_checkpoint", human_approval_node)
    graph.add_node("builder", run_builder)
    graph.add_node("infra", run_infra)
    graph.add_node("monetization", run_monetization)
    graph.add_node("audit", run_audit)

    # Define edges
    graph.set_entry_point("research")
    graph.add_edge("research", "strategy")
    graph.add_edge("strategy", "human_checkpoint")

    # Conditional: approved → build, rejected → retry strategy
    graph.add_conditional_edges(
        "human_checkpoint",
        should_retry_strategy,
        {
            "strategy": "strategy",
            "build": "builder",
            END: END
        }
    )

    # Builder and infra can run in parallel
    graph.add_edge("builder", "infra")          # Sequential for simplicity in 36hrs
    graph.add_edge("infra", "monetization")
    graph.add_edge("monetization", "audit")
    graph.add_edge("audit", END)

    # Add memory for human-in-the-loop checkpoint
    memory = MemorySaver()
    return graph.compile(
        checkpointer=memory,
        interrupt_before=["human_checkpoint"]   # Pause here for human input
    )


# FastAPI entry point usage:
# graph = build_graph()
# config = {"configurable": {"thread_id": session_id}}
# result = graph.invoke({"user_input": idea, "session_id": session_id, ...}, config)
```

---

## 6. Human Checkpoint

```python
# checkpoint.py
from state import AgentState

def human_approval_node(state: AgentState) -> AgentState:
    """
    This node pauses execution via LangGraph interrupt_before.
    The FastAPI endpoint resumes it after receiving human input via POST /approve.
    """
    # Format the strategy for display
    strategy = {
        "product_name": state.get("product_name"),
        "niche": state.get("niche"),
        "icp": state.get("icp"),
        "features": state.get("features"),
        "price_points": state.get("price_points"),
        "rationale": state.get("strategy_rationale"),
    }
    # State is returned as-is; the interrupt mechanism handles the pause
    return {**state, "pending_approval": strategy}

# FastAPI routes needed:
# POST /session/{session_id}/start  → starts the graph
# GET  /session/{session_id}/status → returns current state (including pending strategy)
# POST /session/{session_id}/approve → resumes with approved=True
# POST /session/{session_id}/reject  → resumes with approved=False + feedback
```

---

## 7. AWS CDK Stack (Reusable Template)

```python
# infra/saas_stack.py
from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_dynamodb as dynamodb,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct

class SaasStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        product_name: str,       # e.g. "InvoiceFlow"
        stripe_secret_key: str,  # stored in SSM, not in code
        **kwargs
    ):
        super().__init__(scope, stack_id, **kwargs)

        safe_name = product_name.lower().replace(" ", "-")

        # --- DynamoDB: single-table design ---
        table = dynamodb.Table(
            self, "AppTable",
            table_name=f"{safe_name}-app-table",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # hackathon only
            point_in_time_recovery=False,
        )

        # --- SSM: store Stripe key securely ---
        stripe_param = ssm.StringParameter(
            self, "StripeKey",
            parameter_name=f"/{safe_name}/stripe-secret-key",
            string_value=stripe_secret_key,
            tier=ssm.ParameterTier.STANDARD,
        )

        # --- Lambda execution role ---
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )
        table.grant_read_write_data(lambda_role)
        stripe_param.grant_read(lambda_role)

        # --- Lambda function ---
        fn = lambda_.Function(
            self, "ApiHandler",
            function_name=f"{safe_name}-api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda_src"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "TABLE_NAME": table.table_name,
                "STRIPE_PARAM_PATH": stripe_param.parameter_name,
                "PRODUCT_NAME": product_name,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # --- API Gateway HTTP API ---
        http_api = apigw.HttpApi(
            self, "HttpApi",
            api_name=f"{safe_name}-api",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_headers=["*"],
            )
        )

        lambda_integration = integrations.HttpLambdaIntegration(
            "LambdaIntegration", fn
        )

        http_api.add_routes(
            path="/{proxy+}",
            methods=[apigw.HttpMethod.ANY],
            integration=lambda_integration,
        )

        # --- Outputs (captured by infra_agent.py) ---
        CfnOutput(self, "ApiUrl", value=http_api.api_endpoint)
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "TableArn", value=table.table_arn)
        CfnOutput(self, "FunctionName", value=fn.function_name)
```

```python
# infra/app.py
import aws_cdk as cdk
import os
from saas_stack import SaasStack

app = cdk.App()

SaasStack(
    app,
    f"{os.environ['PRODUCT_NAME'].lower().replace(' ', '-')}-stack",
    product_name=os.environ["PRODUCT_NAME"],
    stripe_secret_key=os.environ["STRIPE_SECRET_KEY"],
    env=cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ.get("AWS_REGION", "us-east-1")
    )
)

app.synth()
```

---

## 8. Key Tool Implementations

### 8.1 Exa Tools

```python
# tools/exa_tools.py
from exa_py import Exa
import os

exa = Exa(api_key=os.environ["EXA_API_KEY"])

def exa_search(query: str, num_results: int = 10) -> list[dict]:
    results = exa.search_and_contents(
        query,
        num_results=num_results,
        use_autoprompt=True,
        text={"max_characters": 1000},
        highlights={"num_sentences": 3},
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "text": r.text,
            "highlights": r.highlights,
            "published_date": r.published_date,
        }
        for r in results.results
    ]

def exa_find_similar(url: str, num_results: int = 5) -> list[dict]:
    results = exa.find_similar_and_contents(
        url,
        num_results=num_results,
        text={"max_characters": 500},
    )
    return [{"title": r.title, "url": r.url, "text": r.text} for r in results.results]
```

### 8.2 Vercel v0 Tools

```python
# tools/v0_tools.py
import httpx
import os

V0_API_KEY = os.environ["V0_API_KEY"]

async def generate_ui(prompt: str, component_name: str = "LandingPage") -> str:
    """Call Vercel v0 API to generate a React component."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://v0.dev/api/generate",
            headers={
                "Authorization": f"Bearer {V0_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "framework": "nextjs",
                "component_name": component_name,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["code"]
```

### 8.3 Stripe Tools

```python
# tools/stripe_tools.py
import stripe
import os

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

def create_product_and_prices(
    product_name: str,
    description: str,
    price_points: list[dict]
) -> dict:
    # Create product
    product = stripe.Product.create(
        name=product_name,
        description=description,
    )

    prices = []
    payment_links = []

    for tier in price_points:
        if tier["price"] == 0:
            continue  # Skip free tier

        price = stripe.Price.create(
            product=product.id,
            unit_amount=int(tier["price"] * 100),  # cents
            currency="usd",
            recurring={"interval": "month"},
            nickname=tier["tier"],
        )

        link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}]
        )

        prices.append({"tier": tier["tier"], "price_id": price.id})
        payment_links.append({"tier": tier["tier"], "url": link.url})

    return {
        "product_id": product.id,
        "prices": prices,
        "payment_links": payment_links,
        "primary_payment_link": payment_links[0]["url"] if payment_links else None,
    }
```

### 8.4 CDK Deploy Tool

```python
# tools/cdk_tools.py
import subprocess
import json
import os

def deploy_saas_stack(product_name: str, stripe_secret_key: str) -> dict:
    env = {
        **os.environ,
        "PRODUCT_NAME": product_name,
        "STRIPE_SECRET_KEY": stripe_secret_key,
    }

    result = subprocess.run(
        ["cdk", "deploy", "--require-approval", "never", "--outputs-file", "/tmp/cdk-outputs.json"],
        cwd="infra/",
        env=env,
        capture_output=True,
        text=True,
        timeout=600,  # 10 min max
    )

    if result.returncode != 0:
        raise RuntimeError(f"CDK deploy failed:\n{result.stderr}")

    with open("/tmp/cdk-outputs.json") as f:
        outputs = json.load(f)

    # Parse CloudFormation outputs
    stack_outputs = list(outputs.values())[0]
    return {
        "api_url": stack_outputs.get("ApiUrl"),
        "table_name": stack_outputs.get("TableName"),
        "table_arn": stack_outputs.get("TableArn"),
        "function_name": stack_outputs.get("FunctionName"),
    }
```

---

## 9. FastAPI Entry Point

```python
# orchestrator/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from graph import build_graph
from state import AgentState
import uuid

app = FastAPI(title="Founder Agent API")
graph = build_graph()
sessions = {}  # In production: use DynamoDB

class StartRequest(BaseModel):
    idea: str

class ApprovalRequest(BaseModel):
    approved: bool
    feedback: str = ""

@app.post("/session/start")
async def start_session(req: StartRequest):
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    initial_state: AgentState = {
        "user_input": req.idea,
        "session_id": session_id,
        "audit_log": [],
        "retry_count": 0,
    }

    # Run until human checkpoint
    result = graph.invoke(initial_state, config)
    sessions[session_id] = config

    return {
        "session_id": session_id,
        "status": "awaiting_approval",
        "strategy": {
            "product_name": result.get("product_name"),
            "niche": result.get("niche"),
            "icp": result.get("icp"),
            "features": result.get("features"),
            "price_points": result.get("price_points"),
            "rationale": result.get("strategy_rationale"),
        }
    }

@app.post("/session/{session_id}/approve")
async def approve_strategy(session_id: str, req: ApprovalRequest):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    config = sessions[session_id]

    # Resume graph after human checkpoint
    result = graph.invoke(
        {"human_approved": req.approved, "human_feedback": req.feedback},
        config
    )

    return {
        "session_id": session_id,
        "status": "complete",
        "live_url": result.get("final_url"),
        "stripe_payment_link": result.get("stripe_payment_link"),
        "decision_brief": result.get("final_brief"),
        "audit_log": result.get("audit_log"),
    }

@app.get("/session/{session_id}/status")
async def get_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    config = sessions[session_id]
    state = graph.get_state(config)
    return {"session_id": session_id, "state": state.values}
```

---

## 10. Environment Variables

```bash
# .env.example

# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=               # for sandbox accounts
AWS_REGION=us-east-1
CDK_DEFAULT_ACCOUNT=

# Vercel
VERCEL_TOKEN=
VERCEL_TEAM_ID=                  # optional
V0_API_KEY=

# Exa
EXA_API_KEY=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=

# LLM (via Vercel AI Gateway)
VERCEL_AI_GATEWAY_URL=           # https://ai-gateway.vercel.sh
ANTHROPIC_API_KEY=               # or OPENAI_API_KEY

# App
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000
```

---

## 11. Requirements

```txt
# requirements.txt
fastapi>=0.111.0
uvicorn>=0.30.0
langgraph>=0.1.0
langchain-anthropic>=0.1.0
exa-py>=1.0.0
stripe>=8.0.0
aws-cdk-lib>=2.140.0
constructs>=10.0.0
boto3>=1.34.0
httpx>=0.27.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

## 12. Build Order (36-Hour Timeline)

### Hours 1–2: Skeleton + Environment
- [ ] Create repo structure
- [ ] Set up `.env` with all API keys
- [ ] Install requirements
- [ ] Bootstrap CDK (`cdk bootstrap`)
- [ ] Verify Exa, Stripe, and Vercel tokens work with a quick test call

### Hours 3–6: Research + Strategy Agents
- [ ] Implement `exa_tools.py`
- [ ] Implement `research_agent.py` — get it returning structured JSON
- [ ] Implement `strategy_agent.py` — get it making a real product decision
- [ ] Test end-to-end: idea → research → strategy output

### Hours 7–10: CDK Stack
- [ ] Build `saas_stack.py` with Lambda + DynamoDB + API GW
- [ ] Test `cdk deploy` manually once
- [ ] Implement `infra_agent.py` to trigger deploy and parse outputs
- [ ] Write minimal `lambda_src/handler.py` (health check + user signup endpoint)

### Hours 11–14: Builder + Monetization Agents
- [ ] Implement `v0_tools.py` — test v0 API call
- [ ] Implement `builder_agent.py` — generate landing page prompt, call v0
- [ ] Implement `vercel_tools.py` — deploy generated code to Vercel
- [ ] Implement `stripe_tools.py` — create product + prices + payment link

### Hours 15–18: LangGraph Orchestration
- [ ] Implement `state.py`
- [ ] Wire up `graph.py` with all agents
- [ ] Add human checkpoint (interrupt_before)
- [ ] Implement `main.py` FastAPI endpoints

### Hours 19–24: Integration + Audit Agent
- [ ] Implement `audit_agent.py`
- [ ] End-to-end test: idea → approved → live URL
- [ ] Replace `{{STRIPE_CHECKOUT_URL}}` placeholders in generated UI
- [ ] Fix integration bugs

### Hours 25–30: Dashboard UI + Polish
- [ ] Use v0 to generate the Founder Agent control panel UI
- [ ] Deploy control panel to Vercel
- [ ] Add real-time status updates (SSE or polling)
- [ ] Add failure handling and retry logic

### Hours 31–34: Demo Recording + Slides
- [ ] Record screen demo: type idea → approve strategy → live URL appears
- [ ] Show audit/decision brief in demo
- [ ] Build `.pptx` slides with embedded recording

### Hours 35–36: Submission
- [ ] Push to public GitHub
- [ ] Verify live URL works
- [ ] Submit on DoraHacks before 11:59pm

---

## 13. Demo Script (for Pitch)

**What to show on screen (embed as screen recording in slides):**

**Act 1 — The Problem (30 seconds)**
- Open IdeaBrowser. Show a real idea: e.g. *AdSpark — AI ad creation for SMBs*
- Show the market research, competitor analysis, execution plan already there
- Pause. Say: *"Great idea. Validated market. Now what? Most founders spend weeks turning this into a product. We built something different."*

**Act 2 — The Demo (4 minutes)**
1. Open Founder Agent UI
2. Paste the IdeaBrowser URL → click **Import**
3. Show the idea populating: product name, market gap, competitors, target customer — all extracted
4. Click **Build This**
5. Show Research Agent augmenting with fresh Exa data (pricing signals, recent competitor moves)
6. Show Strategy Brief appearing:
   - Product: **AdSpark** — *one-click ad creation for SMB marketers*
   - Pricing: Free / $19/mo Pro (undercutting Adobe)
   - Rationale with cited sources from IdeaBrowser + Exa
7. Click **Approve**
8. Show live build status: Builder → Infra → Monetize
9. Show AWS Console — CloudFormation stack deploying (Lambda + DynamoDB + API GW)
10. Show Stripe dashboard — product and payment link created
11. Live URL appears: `adspark.vercel.app` — click it, landing page loads
12. Click Stripe checkout — it works
13. Show Decision Brief: every decision sourced and explained

**Act 3 — The Insight (30 seconds)**
- *"IdeaBrowser finds the opportunity. Founder Agent executes it. From validated idea to live, paying product — in 6 minutes."*
- Show the GitHub repo. Show the AWS console. Show Stripe revenue dashboard.

**Total elapsed: ~6 minutes**

---

## 14. Pitch Talking Points (Judging Criteria Map)

| Judging Dimension | Your Answer |
|---|---|
| **Agent Overview** | 6 specialist agents + 1 orchestrator; each owns one phase of a product launch |
| **Autonomy & Decision-Making** | Strategy agent makes evidence-based product decisions using Exa data — not user instructions |
| **Actions & Tool Use** | Exa search, Vercel v0 generation, Vercel deployment, AWS CDK infrastructure provisioning, Stripe product + payment link creation |
| **Orchestration** | LangGraph supervisor pattern; interrupt-before for human checkpoint; state shared across all agents |
| **Human-in-the-Loop** | Human approves the strategy brief before any code is written; can reject with feedback to trigger re-planning |
| **Failure Handling** | Per-agent retry (max 2); non-critical failures skip with audit log entry; pipeline always completes |
| **Demo & Presentation** | Type one sentence → live, monetised SaaS in 6 minutes — with a full decision brief |

---

## 15. IdeaBrowser Pitch Positioning

| | IdeaBrowser | Founder Agent |
|---|---|---|
| **What it does** | Researches & validates ideas | Builds & deploys the product |
| **Output** | Market brief (read-only) | Live URL + Stripe checkout |
| **Time to value** | Minutes to read | Minutes to launch |
| **User action** | Browse → save → plan | Browse → paste → ship |

They are complementary, not competing. IdeaBrowser is the top of the funnel. Founder Agent is the conversion. Together they close the gap between *"good idea"* and *"live business"* — which has never been closed before.

This framing is memorable on stage because every person in that 10,000-person audience has had a good idea they never built.

---

## 16. Sweep Strategy (Win All Three Prizes)

- **Top 5:** AWS CDK deploys real infra (Lambda + DynamoDB + API GW). Vercel AI Gateway routes all LLM calls. Multi-agent architecture with clear orchestration story.
- **Best Use of Exa:** Research Agent makes 8–12 targeted Exa searches per run. Every strategy decision is sourced from Exa results. Show this in the demo.
- **Best Use of Stripe:** Stripe creates Product + Prices + Payment Links + Checkout. Revenue flows through the agent, not manual config. Show Stripe dashboard in demo.
