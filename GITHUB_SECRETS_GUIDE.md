# GitHub Secrets Configuration Guide

This document lists all the secrets you need to configure in your GitHub repository for the CI/CD pipelines to work.

## How to Add Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add each secret listed below

---

## Required Secrets by Environment

### Development Environment Secrets

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `DEV_DEEPSEEK_API_KEY` | DeepSeek AI API key for development | `sk-dev-abc123...` |
| `DEV_GROQ_API_KEY` | Groq AI API key for development | `gsk_dev_xyz789...` |
| `DEV_APP_URL` | Development application URL | `https://dev.yourdomain.com` |

### Staging Environment Secrets

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `STAGING_DEEPSEEK_API_KEY` | DeepSeek AI API key for staging | `sk-stg-def456...` |
| `STAGING_GROQ_API_KEY` | Groq AI API key for staging | `gsk_stg_uvw012...` |
| `STAGING_APP_URL` | Staging application URL | `https://staging.yourdomain.com` |
| `DOCKER_USERNAME` | Docker Hub username | `yourusername` |
| `DOCKER_PASSWORD` | Docker Hub password/token | `dckr_pat_...` |

### Production Environment Secrets

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `PROD_APP_URL` | Production application URL | `https://yourdomain.com` |
| `DOCKER_USERNAME` | Docker Hub username (same as staging) | `yourusername` |
| `DOCKER_PASSWORD` | Docker Hub password (same as staging) | `dckr_pat_...` |

### Optional Secrets (All Environments)

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `CODECOV_TOKEN` | Codecov coverage reporting token | `a1b2c3d4...` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | `https://hooks.slack.com/...` |
| `SENTRY_DSN` | Sentry error tracking DSN | `https://abc@sentry.io/123` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for notifications | `1234567890:ABC...` |

---

## GitHub Environment Configuration

In addition to secrets, you need to create protected environments:

### 1. Create Environments

Go to **Settings** > **Environments** and create:

1. **development**
   - No special protection rules needed
   - Automatically deploys on push to `dev` branch

2. **staging**
   - Recommended: Add 1 required reviewer
   - Automatically deploys on push to `staging` branch

3. **production**
   - **CRITICAL:** Add 2+ required reviewers
   - Deployment branch restriction: `main` or `master` only
   - Automatically deploys on push to `main`/`master`

### 2. Add Environment-Specific Secrets

For each environment, you can add environment-specific secrets:

1. Go to the environment (Settings > Environments > [environment name])
2. Click **Add secret**
3. Add environment-specific secrets

Example environment-specific secrets:
- Database credentials for each environment
- API keys specific to that environment
- URLs and endpoints

---

## Docker Hub Setup

To push Docker images, you need a Docker Hub account:

1. Create account at https://hub.docker.com
2. Generate an access token:
   - Settings > Security > Access Tokens
   - Click "New Access Token"
   - Copy the token (you won't see it again)
3. Add to GitHub secrets:
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: The access token you generated

---

## Verification Checklist

Before deploying, verify you have:

- [ ] All development secrets configured
- [ ] All staging secrets configured
- [ ] All production secrets configured
- [ ] Docker Hub credentials added
- [ ] Three environments created (development, staging, production)
- [ ] Environment protection rules set for production
- [ ] Branch protection enabled for `main`/`master`
- [ ] Required reviewers configured for production
- [ ] Tested deployment to development first

---

## Security Best Practices

1. **Never commit secrets to Git**
   - Always use GitHub Secrets or environment variables
   - Check `.gitignore` includes `.env` and `.env.*`

2. **Use different secrets per environment**
   - Don't reuse production keys in dev/staging
   - Use separate databases for each environment

3. **Rotate secrets regularly**
   - Change API keys and passwords periodically
   - Update secrets in GitHub when rotated

4. **Limit secret access**
   - Only give repository access to necessary team members
   - Use environment protection rules to control deployments

5. **Monitor secret usage**
   - Review GitHub Actions logs for unauthorized access
   - Set up alerts for failed deployments

---

## Testing Secrets

To test if secrets are properly configured:

1. Push a commit to the `dev` branch
2. Go to **Actions** tab in GitHub
3. Watch the workflow run
4. Check if secrets are properly loaded (they will show as `***` in logs)

If the workflow fails with "secret not found" errors, revisit this guide and ensure all secrets are added.

---

## Need Help?

- Check GitHub documentation: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for deployment procedures
- Contact your DevOps team for assistance

---

**Last Updated:** January 2026
