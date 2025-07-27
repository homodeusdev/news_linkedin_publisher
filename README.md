# 🚀 News LinkedIn Publisher

An intelligent, automated news curation and publishing system that transforms tech news into engaging LinkedIn posts for Spanish-speaking tech professionals.

## 📖 Overview

This AWS Lambda-powered bot automatically:
- 🔍 **Curates** trending tech news using NewsAPI with smart category rotation
- ✨ **Transforms** articles into engaging Spanish content using OpenAI GPT
- 🖼️ **Enhances** posts with relevant images from Unsplash
- 📱 **Publishes** directly to LinkedIn with multiple formats (posts, polls, carousels)
- 🔄 **Rotates** through 35+ tech categories organized in 5 weekly blocks
- 🇲🇽 **Prioritizes** Mexican financial sources for local FinTech content
- 📊 **Generates** interactive polls and PDF carousels automatically
- 🎯 **Scores** content controversy to optimize engagement
- 📝 **Prevents** duplicate posts with intelligent tracking

## 🏗️ Architecture

```
NewsAPI → Content Curation → GPT Processing → Format Selection → LinkedIn Publishing
   ↓              ↓               ↓                  ↓                ↓
Category      AI Rewriting    Controversy        📑 PDF Carousel   📱 Regular Post
Rotation      (Spanish)       Scoring           📊 Interactive Poll  🖼️ Image Post  
              🇲🇽 MX Sources   Image Search      🎯 Smart Targeting   💬 Comments
```

## 🛠️ Tech Stack

- **Runtime**: Python 3.11+ (AWS Lambda)
- **APIs**: LinkedIn v2, OpenAI GPT-3.5/GPT-4, NewsAPI, Unsplash
- **Deployment**: Docker + GitHub Actions
- **Dependencies**: Poetry for package management
- **Document Generation**: FPDF2 for PDF carousels

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
35+ carefully curated tech categories organized in 5 daily blocks:
- **Monday**: AI & Machine Learning (Artificial Intelligence, Deep Learning, NLP, Computer Vision, Generative AI, Prompt Engineering)
- **Tuesday**: AI Applications & Ethics (AI Agents, AI Ethics, Human-AI Interaction, Robotics, Business Strategy, Green Tech)
- **Wednesday**: Emerging Technologies (Scientific Breakthroughs, Quantum Computing, Neuroscience, Cloud Computing, Edge AI)
- **Thursday**: Global FinTech (FinTech, InsurTech, HealthTech, RegTech, Cybersecurity, Blockchain, AI Startups)
- **Friday**: Mexican Economy & FinTech (Economía México, FinTech México, Pagos Digitales MX, Banca Digital, CNBV Regulación)

### 🤖 AI-Powered Content Generation
- Transforms English tech news into engaging Spanish content (GPT-3.5)
- Maintains professional yet approachable millennial tone
- Generates 1,200-2,000 character posts optimized for LinkedIn
- Adds relevant emojis and 3-5 Spanish hashtags
- Includes thought-provoking questions for engagement
- Special prompting for Mexican FinTech impact analysis

### 📊 Multi-Format Publishing
- **📑 PDF Carousels**: Automatically converts first article into 4-slide PDF document
- **🗳️ Interactive Polls**: GPT-4 generates provocative questions with 4 smart options (3-day duration)
- **🖼️ Image Posts**: Traditional posts with Unsplash images and author attribution
- **🎯 Smart Distribution**: 50% of articles become polls, first article becomes carousel

### 🇲🇽 Mexican Content Prioritization
- Auto-detects Mexico/FinTech MX topics from category names
- Prioritizes Mexican financial sources: El Financiero, Expansión, Forbes MX, El Economista
- Spanish-language news search for local content
- CNBV regulation and Mexican financial ecosystem focus

### 📈 Controversy Scoring System
- Analyzes titles and descriptions for 45+ controversy keywords
- Organized by business category (AI bias, job loss, privacy, fraud, regulation)
- 0-5 score system to optimize engagement potential
- Keywords include: "sesgo", "desempleo", "deepfake", "fraude", "CNBV", "regulación"

### 🛡️ Duplicate Prevention
- Tracks published articles in `/tmp/published_articles.txt`
- Prevents republishing the same content
- Persists across Lambda executions during container reuse

## 📱 LinkedIn Integration

### Post Types & Structure
1. **📑 PDF Carousel Posts**: 4-slide documents with titles (≤40 chars) and bullet points (≤60 chars)
2. **🗳️ Poll Posts**: Interactive surveys with provocative questions and 4 distinct options
3. **🖼️ Image Posts**: Traditional posts with Unsplash visuals and photographer attribution
4. **All Posts Include**: Source link, relevant emojis, 3-5 Spanish hashtags

### API Compatibility
- Uses LinkedIn v2 API with latest version headers (202506)
- Implements multiple endpoints: /v2/shares, /rest/posts, /v2/assets
- Document upload system for PDF carousels
- Poll creation with 3-day duration settings
- UGC (User Generated Content) endpoints
- Proper error handling and fallback mechanisms

## 🔧 Configuration

### Category Customization
Modify the `CATEGORY_BLOCKS` list in `lambda_function.py` to adjust daily topic rotation:

```python
CATEGORY_BLOCKS = [
    # Monday - AI & ML Block
    ["Artificial Intelligence", "Machine Learning", "Deep Learning"],
    # Tuesday - AI Applications
    ["AI Agents & Automation", "AI Ethics & Regulation"],
    # ... customize your 5 daily blocks
]
```

### Content Style Adjustment
- **Main Content**: Customize GPT-3.5 prompt in `summarize_and_rewrite()` (line 231)
- **Poll Generation**: Adjust GPT-4 prompt in `generate_dynamic_poll()` (line 491)
- **PDF Slides**: Modify slide structure in `generate_slides()` (line 276)

### Format Distribution
- **PDF Carousels**: Always first article (hardcoded in `main()` line 452)
- **Polls**: 50% of remaining articles (`num_polls = len(processed) // 2`)
- **Regular Posts**: Remaining articles with images

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
- Successful LinkedIn posts by format (regular/poll/carousel)
- Controversy scores and engagement correlation
- API rate limit usage (NewsAPI, OpenAI, LinkedIn, Unsplash)
- Error rates and types
- Mexican vs global content distribution

## 🚨 Troubleshooting

### Common Issues

**Import Errors**: Ensure all dependencies are in deployment package
```bash
poetry export -f requirements.txt --without-hashes -o build/requirements.txt
```

**API Rate Limits**: 
- NewsAPI: 1000 requests/day (free tier)
- LinkedIn: 500 posts/day per person
- OpenAI: Varies by plan (GPT-3.5 + GPT-4 usage)
- Unsplash: 50 requests/hour (free tier)

**PDF Generation Issues**: 
- FPDF2 encoding problems with special characters
- Large PDF upload failures (check LinkedIn asset limits)

**Lambda Timeouts**: Increase timeout for PDF generation and image processing (recommended: 5 minutes)

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
