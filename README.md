# 🚀 News LinkedIn Publisher

An intelligent, automated news curation and publishing system that transforms tech news into engaging LinkedIn posts for Spanish-speaking tech professionals.

## 📖 Overview

This AWS Lambda-powered bot automatically:
- 🔍 **Curates** trending tech news using NewsAPI with smart category rotation
- ✨ **Transforms** articles into engaging Spanish content using OpenAI GPT
- 🖼️ **Enhances** posts with relevant images from Unsplash
- 📱 **Publishes** directly to LinkedIn with proper formatting and links
- 🔄 **Rotates** through 28 tech categories on a weekly cycle
- 📝 **Prevents** duplicate posts with intelligent tracking

## 🏗️ Architecture

```
NewsAPI → Content Curation → GPT Processing → Unsplash Images → LinkedIn Publishing
   ↓              ↓               ↓              ↓              ↓
Category      AI Rewriting    Image Search   Post Creation   Comment Link
Rotation      (Spanish)       & Upload       with Media      Addition
```

## 🛠️ Tech Stack

- **Runtime**: Python 3.11+ (AWS Lambda)
- **APIs**: LinkedIn v2, OpenAI GPT-3.5, NewsAPI, Unsplash
- **Deployment**: Docker + GitHub Actions
- **Dependencies**: Poetry for package management

## 📋 Requirements

### System Requirements
- Python 3.11 or higher
- Docker (for deployment)
- Poetry (for dependency management)

### API Keys Required
- `NEWSAPI_KEY` - For fetching tech news
- `OPENAI_API_KEY` - For content generation and rewriting
- `LINKEDIN_ACCESS_TOKEN` - For posting to LinkedIn
- `LINKEDIN_PERSON_ID` - Your LinkedIn person ID
- `UNSPLASH_ACCESS_KEY` - For fetching relevant images

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd news_linkedin_publisher
```

### 2. Install Dependencies
```bash
poetry install
```

### 3. Environment Setup
Create a `.env` file:
```env
NEWSAPI_KEY=your_newsapi_key
OPENAI_API_KEY=your_openai_key
LINKEDIN_ACCESS_TOKEN=your_linkedin_token
LINKEDIN_PERSON_ID=your_linkedin_person_id
UNSPLASH_ACCESS_KEY=your_unsplash_key
```

### 4. Local Testing
```bash
poetry run python lambda_function.py
```

## 🏭 Deployment

### Automated Deployment (Recommended)
The project includes GitHub Actions for automated deployment:

1. **Configure Secrets** in your GitHub repository:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - All API keys as environment variables

2. **Push to main branch** - deployment happens automatically!

### Manual Deployment
```bash
# Build Docker image
docker build --no-cache -t lambda-package .

# Extract deployment package
docker create --name temp_container lambda-package
docker cp temp_container:/var/task/deployment_package.zip ./deployment_package.zip
docker rm temp_container

# Deploy to AWS Lambda
aws lambda update-function-code \
  --function-name news_linkedin_publisher \
  --zip-file fileb://deployment_package.zip
```

## 🎯 Features

### 🔄 Smart Category Rotation
28 carefully curated tech categories rotating weekly:
- **Week 1**: AI & Machine Learning Focus
- **Week 2**: AI Applications & Ethics  
- **Week 3**: Emerging Technologies
- **Week 4**: FinTech & Digital Economy

### 🤖 AI-Powered Content Generation
- Transforms English tech news into engaging Spanish content
- Maintains professional yet approachable tone
- Adds relevant emojis and hashtags
- Includes thought-provoking questions for engagement

### 📸 Visual Enhancement
- Automatic image search based on article content
- Proper attribution to Unsplash photographers
- AI-generated alt text for accessibility
- Optimized for LinkedIn's image requirements

### 🛡️ Duplicate Prevention
- Tracks published articles in `/tmp/published_articles.txt`
- Prevents republishing the same content
- Persists across Lambda executions during container reuse

## 📱 LinkedIn Integration

### Post Structure
1. **Main Post**: Article title + AI-generated summary + author credit
2. **First Comment**: Original article link (to avoid algorithm penalties)
3. **Image**: Relevant visual with proper alt text
4. **Hashtags**: 3-5 relevant Spanish tech hashtags

### API Compatibility
- Uses LinkedIn v2 API
- Implements UGC (User Generated Content) endpoints
- Supports both text and image posts
- Proper error handling and retries

## 🔧 Configuration

### Category Customization
Modify the `CATEGORIES` list in `lambda_function.py` to adjust topics:

```python
CATEGORIES = [
    "Artificial Intelligence",
    "Machine Learning", 
    # Add your categories...
]
```

### Content Style Adjustment
Customize the GPT prompt in `summarize_and_rewrite()` function to match your voice and audience.

## 🏃‍♂️ Local Development

### Running Tests
```bash
poetry run pytest tests/
```

### Debugging
Enable detailed logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Monitoring

### CloudWatch Logs
Monitor Lambda execution:
```bash
aws logs tail /aws/lambda/news_linkedin_publisher --follow
```

### Success Metrics
- Articles processed per execution
- Successful LinkedIn posts
- API rate limit usage
- Error rates and types

## 🚨 Troubleshooting

### Common Issues

**Import Errors**: Ensure all dependencies are in deployment package
```bash
poetry export -f requirements.txt --without-hashes -o build/requirements.txt
```

**API Rate Limits**: 
- NewsAPI: 1000 requests/day (free tier)
- LinkedIn: 500 posts/day per person
- OpenAI: Varies by plan

**Lambda Timeouts**: Increase timeout for image processing (recommended: 5 minutes)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **NewsAPI** for reliable tech news feeds
- **OpenAI** for intelligent content transformation  
- **Unsplash** for beautiful, free images
- **LinkedIn** for professional networking platform
- **AWS Lambda** for serverless execution

---

**Built with ❤️ for the Spanish-speaking tech community by a Mexican AI Engineer**
