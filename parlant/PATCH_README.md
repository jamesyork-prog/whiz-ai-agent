# Parlant SDK Gemini Model Patch

## Overview

This directory contains a permanent patch for the Parlant SDK to update hardcoded Gemini model references from the deprecated `gemini-1.5-flash` to the current `gemini-2.5-flash` model.

## Problem

The Parlant SDK (as of version 3.x) has hardcoded references to `gemini-1.5-flash` in its `gemini_service.py` file. This model is no longer available in the Gemini API v1beta, causing 404 errors when the SDK tries to use it for token counting and other operations.

## Solution

The `patch_gemini_model.py` script automatically patches the Parlant SDK during Docker image build to replace all occurrences of `gemini-1.5-flash` with `gemini-2.5-flash`.

## How It Works

1. **Build Time**: The Dockerfile runs `patch_gemini_model.py` after installing Python dependencies
2. **Patch Script**: Locates and modifies `/usr/local/lib/python3.11/site-packages/parlant/adapters/nlp/gemini_service.py`
3. **Replacement**: Changes all `gemini-1.5-flash` references to `gemini-2.5-flash`

## Files

- `patch_gemini_model.py`: Python script that performs the patching
- `Dockerfile`: Updated to run the patch script during build

## Verification

To verify the patch was applied successfully:

```bash
# Check build logs
docker-compose build parlant 2>&1 | grep -E "(patch|Patch|✓|✅)"

# Verify in running container
docker-compose exec parlant grep "gemini-2.5-flash" /usr/local/lib/python3.11/site-packages/parlant/adapters/nlp/gemini_service.py
```

You should see:
- Build output: `✅ Patch applied successfully!`
- File contains: `gemini-2.5-flash` instead of `gemini-1.5-flash`

## Maintenance

This patch is applied automatically every time the Docker image is built. No manual intervention is required.

If Parlant SDK is updated and the patch fails, check:
1. The file path in `patch_gemini_model.py` is still correct
2. The pattern to replace still exists in the new version
3. Update the patch script if the SDK structure has changed

## Alternative Solutions

If you prefer not to patch the SDK, you could:
1. Wait for an official Parlant SDK update
2. Use OpenAI provider instead (`LLM_PROVIDER=openai` in `.env`)
3. Fork and maintain a custom version of the Parlant SDK
