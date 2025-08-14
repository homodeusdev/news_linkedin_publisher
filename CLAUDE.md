# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Spanish-language AI-powered news curation and LinkedIn publishing bot that runs as an AWS Lambda function. It automatically fetches tech news, transforms it into engaging Spanish content using OpenAI GPT, and publishes it to LinkedIn in multiple formats (posts, polls, PDF carousels).

## Development Commands

### Local Development
```bash
# Install dependencies
poetry install

# Run locally for testing
poetry run python lambda_function.py

# Run tests
poetry run pytest tests/
```

### Docker and Deployment
```bash
# Build deployment package (used in CI/CD)
docker build --no-cache -t lambda-package .

# Extract deployment package manually
docker create --name temp_container lambda-package
docker cp temp_container:/var/task/deployment_package.zip ./deployment_package.zip
docker rm temp_container

# Deploy to AWS Lambda (manual)
aws lambda update-function-code \
  --function-name news_linkedin_publisher \
  --zip-file fileb://deployment_package.zip \
  --region us-east-2
```

### Export Dependencies
```bash
# Export Poetry dependencies for Lambda (if needed)
poetry export -f requirements.txt --without-hashes -o requirements.txt
```

## Architecture

### Core Components

1. **News Curation** (`fetch_news_biased()` at line 191): Intelligent news fetching with bias toward Mexican/FinTech content (~60% Mexican, ~40% global)
2. **Content Generation** (`summarize_and_rewrite()` at line 316): GPT-3.5 transforms English articles into Spanish LinkedIn posts (1200-2000 chars)
3. **Multi-Format Publishing**: 
   - PDF Carousels (`build_pdf()` at line 394): 4-slide documents with titles ≤40 chars
   - Interactive Polls (`generate_dynamic_poll()` at line 580): GPT-4 generates provocative questions
   - Regular Image Posts: Traditional posts with Unsplash images

### Content Strategy

- **Category Rotation**: 5 daily content blocks organized by weekday (35+ tech categories total)
- **Mexican Focus**: Prioritizes Mexican financial sources (El Financiero, Expansión, Forbes MX, El Economista)
- **Controversy Scoring**: 45+ keywords analyze engagement potential (0-5 scale)
- **Duplicate Prevention**: Tracks published articles in `/tmp/published_articles.txt`

### LinkedIn Integration

Uses LinkedIn v2 API with multiple endpoints:
- `/v2/shares` for regular posts
- `/rest/posts` for polls and document carousels
- `/v2/assets` for PDF upload system
- Latest API version headers (202506)

## Key Configuration

### Environment Variables Required
- `NEWSAPI_KEY` - News fetching
- `OPENAI_API_KEY` - Content generation (GPT-3.5 + GPT-4)
- `LINKEDIN_ACCESS_TOKEN` - LinkedIn posting
- `LINKEDIN_PERSON_ID` - LinkedIn user ID
- `UNSPLASH_ACCESS_KEY` - Image fetching
- `TOTAL_ARTICLES` - Number of articles per execution (default: 8)

### Content Customization

#### Category Blocks (`CATEGORY_BLOCKS` at line 45)
Modify the 5 daily content blocks to adjust topic rotation:
- Block 1 (Monday): AI & Machine Learning
- Block 2 (Tuesday): AI Applications & Ethics  
- Block 3 (Wednesday): Emerging Technologies
- Block 4 (Thursday): Global FinTech
- Block 5 (Friday): Mexican Economy & FinTech

#### Content Prompts
- Main content generation: `summarize_and_rewrite()` line 321-334
- Poll generation: `generate_dynamic_poll()` line 584-595
- PDF slide structure: `generate_slides()` line 366-370

### Publishing Distribution
- **All articles become polls** (current implementation at line 541-547)
- Format can be adjusted in `main()` function
- Originally designed for mixed formats: 50% polls, first article as PDF carousel, rest as regular posts

## Lambda Deployment

### Automated (GitHub Actions)
- Triggers on push to `main` branch
- Uses `.github/workflows/deploy.yml`
- Requires AWS credentials in GitHub Secrets
- Builds Docker image and deploys automatically

### Manual Process
1. Build Docker image with dependencies
2. Extract deployment ZIP package  
3. Upload to AWS Lambda function `news_linkedin_publisher`
4. Function runs with Python 3.11 runtime

## API Rate Limits

- **NewsAPI**: 1000 requests/day (free tier)
- **OpenAI**: Varies by plan (uses both GPT-3.5 and GPT-4)
- **LinkedIn**: 500 posts/day per person
- **Unsplash**: 50 requests/hour (free tier)

## Technical Notes

- **Language Detection**: Auto-detects Mexico/FinTech topics for Spanish vs English queries
- **Error Handling**: Comprehensive fallbacks for API failures
- **PDF Generation**: Uses FPDF2 with UTF-8 encoding for Spanish content
- **Image Attribution**: Includes photographer credits for Unsplash images
- **Controversy Analysis**: Sophisticated keyword scoring system across business categories