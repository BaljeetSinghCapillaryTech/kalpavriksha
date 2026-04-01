#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AIDLC Setup Script
# Sets up Claude Code CLI + authentication for the AIDLC pipeline.
# Run this once before using `claude --agent aidlc`.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🚀 AIDLC — AI Development Lifecycle Setup${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[$1/$TOTAL_STEPS]${NC} $2"
}

print_success() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "  ${RED}❌ $1${NC}"
}

print_info() {
    echo -e "  ${CYAN}ℹ️  $1${NC}"
}

TOTAL_STEPS=5

print_header

# ─────────────────────────────────────────────────────────────
# Step 1: Check Claude Code CLI
# ─────────────────────────────────────────────────────────────
print_step 1 "Checking Claude Code CLI..."

if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    print_success "Claude Code CLI found: v${CLAUDE_VERSION}"
else
    print_error "Claude Code CLI not found."
    echo ""
    echo -e "  Install Claude Code CLI first:"
    echo -e "  ${BOLD}npm install -g @anthropic-ai/claude-code${NC}"
    echo ""
    echo -e "  Or if you prefer npx (no global install):"
    echo -e "  ${BOLD}npx @anthropic-ai/claude-code${NC}"
    echo ""
    read -p "  Install now via npm? (y/n): " INSTALL_CHOICE
    if [[ "$INSTALL_CHOICE" == "y" || "$INSTALL_CHOICE" == "Y" ]]; then
        echo "  Installing..."
        npm install -g @anthropic-ai/claude-code
        print_success "Claude Code CLI installed."
    else
        echo ""
        print_error "Cannot proceed without Claude Code CLI. Install it and re-run this script."
        exit 1
    fi
fi

# ─────────────────────────────────────────────────────────────
# Step 2: Check Authentication
# ─────────────────────────────────────────────────────────────
print_step 2 "Checking authentication..."

AUTH_STATUS=$(claude auth status 2>/dev/null || echo '{"loggedIn": false}')
IS_LOGGED_IN=$(echo "$AUTH_STATUS" | grep -o '"loggedIn": *true' || true)

if [[ -n "$IS_LOGGED_IN" ]]; then
    AUTH_METHOD=$(echo "$AUTH_STATUS" | grep -o '"authMethod": *"[^"]*"' | cut -d'"' -f4)
    print_success "Already authenticated (method: ${AUTH_METHOD})"
else
    print_warning "Not authenticated. Let's set that up."
    echo ""
    echo -e "  ${BOLD}Choose authentication method:${NC}"
    echo ""
    echo -e "  [1] ${GREEN}OAuth Login (recommended)${NC}"
    echo -e "      Sign in with your Anthropic account via browser."
    echo -e "      Requires a Claude Pro/Team/Enterprise subscription."
    echo -e "      No API key needed — uses your subscription quota."
    echo ""
    echo -e "  [2] ${BLUE}API Key${NC}"
    echo -e "      Use an Anthropic API key (from console.anthropic.com)."
    echo -e "      Billed per token usage against your API account."
    echo -e "      Key is stored securely in your system keychain."
    echo ""
    echo -e "  [3] ${YELLOW}Amazon Bedrock${NC}"
    echo -e "      Use Claude via AWS Bedrock."
    echo -e "      Requires AWS credentials configured locally."
    echo ""
    echo -e "  [4] ${YELLOW}Google Vertex AI${NC}"
    echo -e "      Use Claude via Google Cloud Vertex AI."
    echo -e "      Requires GCP credentials configured locally."
    echo ""
    read -p "  Enter choice (1-4): " AUTH_CHOICE
    echo ""

    case "$AUTH_CHOICE" in
        1)
            print_info "Opening browser for OAuth login..."
            claude auth login
            ;;
        2)
            echo -e "  Get your API key from: ${BOLD}https://console.anthropic.com/settings/keys${NC}"
            echo ""
            read -sp "  Enter your Anthropic API key (sk-ant-...): " API_KEY
            echo ""

            if [[ -z "$API_KEY" ]]; then
                print_error "No key provided. Skipping."
            elif [[ ! "$API_KEY" =~ ^sk-ant- ]]; then
                print_warning "Key doesn't start with 'sk-ant-'. Are you sure this is correct?"
                read -p "  Continue anyway? (y/n): " CONFIRM
                if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
                    print_error "Aborted. Re-run the script with a valid key."
                    exit 1
                fi
            fi

            if [[ -n "$API_KEY" ]]; then
                # Store key in environment config
                SHELL_RC=""
                if [[ -f "$HOME/.zshrc" ]]; then
                    SHELL_RC="$HOME/.zshrc"
                elif [[ -f "$HOME/.bashrc" ]]; then
                    SHELL_RC="$HOME/.bashrc"
                elif [[ -f "$HOME/.bash_profile" ]]; then
                    SHELL_RC="$HOME/.bash_profile"
                fi

                # Check if already set
                if grep -q "ANTHROPIC_API_KEY" "$SHELL_RC" 2>/dev/null; then
                    print_warning "ANTHROPIC_API_KEY already exists in $SHELL_RC"
                    read -p "  Overwrite? (y/n): " OVERWRITE
                    if [[ "$OVERWRITE" == "y" || "$OVERWRITE" == "Y" ]]; then
                        # Remove old entry
                        if [[ "$(uname)" == "Darwin" ]]; then
                            sed -i '' '/ANTHROPIC_API_KEY/d' "$SHELL_RC"
                        else
                            sed -i '/ANTHROPIC_API_KEY/d' "$SHELL_RC"
                        fi
                    else
                        print_info "Keeping existing key."
                        API_KEY=""
                    fi
                fi

                if [[ -n "$API_KEY" ]]; then
                    echo "" >> "$SHELL_RC"
                    echo "# AIDLC — Anthropic API Key (added by aidlc-setup)" >> "$SHELL_RC"
                    echo "export ANTHROPIC_API_KEY=\"$API_KEY\"" >> "$SHELL_RC"
                    export ANTHROPIC_API_KEY="$API_KEY"
                    print_success "API key saved to $SHELL_RC"
                    print_info "Key is active for this session. New terminals will auto-load it."
                fi
            fi
            ;;
        3)
            echo -e "  ${BOLD}Amazon Bedrock Setup${NC}"
            echo ""
            echo -e "  Prerequisites:"
            echo -e "    • AWS CLI configured (aws configure)"
            echo -e "    • Claude model access enabled in Bedrock console"
            echo ""

            SHELL_RC=""
            if [[ -f "$HOME/.zshrc" ]]; then
                SHELL_RC="$HOME/.zshrc"
            elif [[ -f "$HOME/.bashrc" ]]; then
                SHELL_RC="$HOME/.bashrc"
            fi

            read -p "  AWS Region (e.g., us-east-1): " AWS_REGION
            read -p "  AWS Profile (leave blank for default): " AWS_PROFILE

            {
                echo ""
                echo "# AIDLC — Amazon Bedrock config (added by aidlc-setup)"
                echo "export CLAUDE_CODE_USE_BEDROCK=1"
                [[ -n "$AWS_REGION" ]] && echo "export AWS_REGION=\"$AWS_REGION\""
                [[ -n "$AWS_PROFILE" ]] && echo "export AWS_PROFILE=\"$AWS_PROFILE\""
            } >> "$SHELL_RC"

            export CLAUDE_CODE_USE_BEDROCK=1
            [[ -n "$AWS_REGION" ]] && export AWS_REGION="$AWS_REGION"
            [[ -n "$AWS_PROFILE" ]] && export AWS_PROFILE="$AWS_PROFILE"

            print_success "Bedrock config saved to $SHELL_RC"
            ;;
        4)
            echo -e "  ${BOLD}Google Vertex AI Setup${NC}"
            echo ""
            echo -e "  Prerequisites:"
            echo -e "    • gcloud CLI configured (gcloud auth login)"
            echo -e "    • Claude model access enabled in Vertex AI"
            echo ""

            SHELL_RC=""
            if [[ -f "$HOME/.zshrc" ]]; then
                SHELL_RC="$HOME/.zshrc"
            elif [[ -f "$HOME/.bashrc" ]]; then
                SHELL_RC="$HOME/.bashrc"
            fi

            read -p "  GCP Project ID: " GCP_PROJECT
            read -p "  GCP Region (e.g., us-east5): " GCP_REGION

            {
                echo ""
                echo "# AIDLC — Google Vertex AI config (added by aidlc-setup)"
                echo "export CLAUDE_CODE_USE_VERTEX=1"
                [[ -n "$GCP_PROJECT" ]] && echo "export CLOUD_ML_PROJECT_ID=\"$GCP_PROJECT\""
                [[ -n "$GCP_REGION" ]] && echo "export CLOUD_ML_REGION=\"$GCP_REGION\""
            } >> "$SHELL_RC"

            export CLAUDE_CODE_USE_VERTEX=1
            [[ -n "$GCP_PROJECT" ]] && export CLOUD_ML_PROJECT_ID="$GCP_PROJECT"
            [[ -n "$GCP_REGION" ]] && export CLOUD_ML_REGION="$GCP_REGION"

            print_success "Vertex AI config saved to $SHELL_RC"
            ;;
        *)
            print_error "Invalid choice. Re-run the script."
            exit 1
            ;;
    esac

    # Verify auth after setup
    echo ""
    AUTH_STATUS_AFTER=$(claude auth status 2>/dev/null || echo '{"loggedIn": false}')
    IS_LOGGED_IN_AFTER=$(echo "$AUTH_STATUS_AFTER" | grep -o '"loggedIn": *true' || true)
    if [[ -n "$IS_LOGGED_IN_AFTER" ]]; then
        print_success "Authentication verified."
    else
        if [[ "$AUTH_CHOICE" == "2" || "$AUTH_CHOICE" == "3" || "$AUTH_CHOICE" == "4" ]]; then
            print_info "Auth configured. It will take effect when you run claude."
        else
            print_warning "Authentication may not have completed. Try running: claude auth login"
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────
# Step 3: Verify AIDLC Agent
# ─────────────────────────────────────────────────────────────
print_step 3 "Verifying AIDLC agent..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -f "$PROJECT_ROOT/.claude/agents/aidlc.md" ]]; then
    print_success "AIDLC agent found at .claude/agents/aidlc.md"
else
    print_error "AIDLC agent not found at .claude/agents/aidlc.md"
    print_info "Make sure you're running this script from the project root."
    exit 1
fi

if [[ -f "$PROJECT_ROOT/.claude/skills/workflow/SKILL.md" ]]; then
    SKILL_COUNT=$(ls "$PROJECT_ROOT/.claude/skills/"/*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    print_success "Workflow orchestrator found. ${SKILL_COUNT} skills detected."
else
    print_warning "Workflow skill not found. AIDLC skills may not be set up."
fi

if [[ -f "$PROJECT_ROOT/.claude/skills/GUARDRAILS.md" ]]; then
    print_success "Development guardrails found."
else
    print_warning "GUARDRAILS.md not found. Guardrail enforcement will be skipped."
fi

# ─────────────────────────────────────────────────────────────
# Step 4: Optional Enhancements
# ─────────────────────────────────────────────────────────────
print_step 4 "Checking optional enhancements..."

# Check jdtls
if [[ -f "$HOME/.jdtls-daemon/jdtls.py" ]]; then
    print_success "jdtls (Java LSP) found — semantic code navigation enabled."
else
    print_info "jdtls not found — phases will use grep/file reads for code navigation."
    echo -e "      To enable LSP: install jdtls-daemon at ~/.jdtls-daemon/"
fi

# Check historian MCP
if claude mcp list 2>/dev/null | grep -q "historian"; then
    print_success "Historian MCP found — cross-session memory enabled."
else
    print_info "Historian MCP not found — each session starts fresh."
    echo -e "      To enable: claude mcp add claude-historian-mcp -- npx claude-historian-mcp"
fi

# Check poppler (for PDF BRD support)
if command -v pdftotext &> /dev/null; then
    print_success "poppler found — PDF BRD input supported."
else
    print_info "poppler not found — PDF BRDs won't be readable."
    echo -e "      To enable: brew install poppler (macOS) or apt install poppler-utils (Linux)"
fi

# ─────────────────────────────────────────────────────────────
# Step 5: Summary
# ─────────────────────────────────────────────────────────────
print_step 5 "Setup complete!"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  ✅ AIDLC is ready to use${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}To start the AIDLC pipeline:${NC}"
echo ""
echo -e "    cd $PROJECT_ROOT"
echo -e "    ${GREEN}claude --agent aidlc${NC}"
echo ""
echo -e "  ${BOLD}Quick commands:${NC}"
echo ""
echo -e "    ${GREEN}claude --agent aidlc${NC}                             Interactive menu"
echo -e "    ${GREEN}claude --agent aidlc -p \"workflow <path>\"${NC}        Full pipeline"
echo -e "    ${GREEN}claude --agent aidlc -p \"phase developer <path>\"${NC} Single phase"
echo -e "    ${GREEN}claude --agent aidlc -p \"revert <path>\"${NC}         Roll back"
echo -e "    ${GREEN}claude --agent aidlc -p \"status <path>\"${NC}         Check progress"
echo ""
echo -e "  ${BOLD}Documentation:${NC}"
echo -e "    .claude/skills/README-AIDLC.md  — Full user guide"
echo -e "    .claude/skills/README.md        — Skills reference"
echo -e "    .claude/skills/GUARDRAILS.md    — Development guardrails"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
