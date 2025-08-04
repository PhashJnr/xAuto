import openai
import requests
import json
import os
import time
import hashlib
from typing import Dict, List, Optional
from utils import log_to_file
from datetime import datetime, timedelta
import threading
import queue
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = None

class APIRateLimiter:
    """Rate limiter to prevent excessive API calls"""
    
    def __init__(self, max_calls_per_minute: int = 60, max_calls_per_hour: int = 1000):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_hour = max_calls_per_hour
        self.minute_calls = []
        self.hour_calls = []
        self.lock = threading.Lock()
    
    def can_make_call(self) -> bool:
        """Check if we can make an API call"""
        now = time.time()
        
        with self.lock:
            # Clean old calls
            self.minute_calls = [t for t in self.minute_calls if now - t < 60]
            self.hour_calls = [t for t in self.hour_calls if now - t < 3600]
            
            # Check limits
            if len(self.minute_calls) >= self.max_calls_per_minute:
                return False
            if len(self.hour_calls) >= self.max_calls_per_hour:
                return False
            
            return True
    
    def record_call(self):
        """Record that an API call was made"""
        now = time.time()
        with self.lock:
            self.minute_calls.append(now)
            self.hour_calls.append(now)

class APICache:
    """Cache to prevent duplicate API calls"""
    
    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self.lock = threading.Lock()
    
    def _get_cache_key(self, content: str, prompt_type: str) -> str:
        """Generate cache key from content and prompt type"""
        return hashlib.md5(f"{content}:{prompt_type}".encode()).hexdigest()
    
    def get(self, content: str, prompt_type: str) -> Optional[str]:
        """Get cached result"""
        key = self._get_cache_key(content, prompt_type)
        with self.lock:
            if key in self.cache:
                timestamp, result = self.cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    return result
                else:
                    del self.cache[key]
        return None
    
    def set(self, content: str, prompt_type: str, result: str):
        """Cache a result"""
        key = self._get_cache_key(content, prompt_type)
        with self.lock:
            # Clean old entries if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
                del self.cache[oldest_key]
            
            self.cache[key] = (time.time(), result)

class CostTracker:
    """Track API costs to prevent budget overruns"""
    
    def __init__(self, daily_budget: float = 10.0, monthly_budget: float = 100.0):
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.daily_costs = {}
        self.monthly_costs = {}
        self.lock = threading.Lock()
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for OpenAI API call"""
        # OpenAI GPT-4 pricing: $0.03/1K input, $0.06/1K output
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        return input_cost + output_cost
    
    def can_afford_call(self, estimated_tokens: int) -> bool:
        """Check if we can afford the API call"""
        estimated_cost = self.estimate_cost(estimated_tokens, estimated_tokens // 2)
        
        with self.lock:
            today = datetime.now().strftime('%Y-%m-%d')
            this_month = datetime.now().strftime('%Y-%m')
            
            daily_cost = self.daily_costs.get(today, 0)
            monthly_cost = self.monthly_costs.get(this_month, 0)
            
            return daily_cost + estimated_cost <= self.daily_budget and monthly_cost + estimated_cost <= self.monthly_budget
    
    def record_cost(self, input_tokens: int, output_tokens: int):
        """Record the cost of an API call"""
        cost = self.estimate_cost(input_tokens, output_tokens)
        
        with self.lock:
            today = datetime.now().strftime('%Y-%m-%d')
            this_month = datetime.now().strftime('%Y-%m')
            
            self.daily_costs[today] = self.daily_costs.get(today, 0) + cost
            self.monthly_costs[this_month] = self.monthly_costs.get(this_month, 0) + cost

class OpenAIProvider:
    """OpenAI GPT integration - Focused and optimized"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.name = f"OpenAI {model.upper()}"
        self.model = model
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.is_configured = bool(self.api_key)
        self.max_retries = 3
        
        # Initialize optimization components
        self.rate_limiter = APIRateLimiter()
        self.cache = APICache()
        self.cost_tracker = CostTracker()
        
        if self.api_key:
            global client
            client = openai.OpenAI(api_key=self.api_key)
            log_to_file('ai_integration', f"OpenAI provider initialized with model: {model}")
            log_to_file('ai_integration', f"API key configured: {'Yes' if self.is_configured else 'No'}")
    
    def test_connection(self, api_key: str = None) -> bool:
        """Test OpenAI API connection"""
        try:
            # Use provided API key if given, otherwise use the one from initialization
            test_key = api_key if api_key else self.api_key
            if not test_key:
                log_to_file('ai_integration', "OpenAI test_connection: No API key provided")
                return False
            
            # Validate API key format
            if not test_key.startswith('sk-'):
                log_to_file('ai_integration', "OpenAI test_connection: Invalid API key format")
                return False
            
            # Create test client
            test_client = openai.OpenAI(api_key=test_key)
            
            # Test with a simple completion
            response = test_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use a more reliable model for testing
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=5
            )
            
            # If we get here, the connection was successful
            log_to_file('ai_integration', "OpenAI test_connection: Success")
            return True
            
        except Exception as e:
            log_to_file('ai_integration', f"OpenAI connection test failed: {e}")
            return False
    
    def generate_comment(self, tweet_content: str, analysis: Dict, custom_prompt: str = None) -> str:
        """Generate an engaging comment for a tweet"""
        if not self.is_configured:
            log_to_file('ai_integration', "OpenAI not configured, using fallback")
            return "Great post! Thanks for sharing."
        
        try:
            # Add a random element to prevent caching and ensure new comments
            import random
            random_suffix = f" [unique_{random.randint(1000, 9999)}]"
            content_for_cache = tweet_content + random_suffix
            
            # Check if we should skip this call (but don't use cache for comments)
            skip, cached_result = self._should_skip_call(content_for_cache, "comment")
            if skip and not cached_result:
                log_to_file('ai_integration', "Rate limited or budget exceeded, using fallback")
                return "Great post! Thanks for sharing."
            
            # Create context-aware prompt
            prompt = self._build_comment_prompt(tweet_content, analysis, custom_prompt)
            
            log_to_file('ai_integration', f"Making OpenAI API call for comment generation")
            
            # Make API call with retries
            for attempt in range(self.max_retries):
                try:
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a social media expert who creates engaging, authentic comments. Be conversational, relevant, and add value to the discussion."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.8,  # Increased temperature for more variety
                        presence_penalty=0.1,
                        frequency_penalty=0.1
                    )
                    
                    result = response.choices[0].message.content.strip()
                    
                    # Record successful call but don't cache comments
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    self._record_successful_call_no_cache(tweet_content, "comment", result, input_tokens, output_tokens)
                    
                    log_to_file('ai_integration', f"Successfully generated comment: {result[:50]}...")
                    return result
                    
                except Exception as e:
                    self._record_failed_call(str(e))
                    log_to_file('ai_integration', f"OpenAI API call failed (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise e
            
        except Exception as e:
            log_to_file('ai_integration', f"OpenAI error in generate_comment: {e}")
            return "Interesting post! Thanks for sharing."
    
    def generate_comment_from_tweet(self, tweet_content: str, custom_prompt: str = None) -> str:
        """Generate a comment based only on tweet content (no comments analysis)"""
        try:
            # Check if we should skip this call (but disable for auto yapping)
            should_skip, cached_result = self._should_skip_call(tweet_content, "tweet_comment")
            
            # For auto yapping, we want unique replies, so skip caching if content contains unique markers
            if "[Account:" in tweet_content or "[Timestamp:" in tweet_content:
                should_skip = False
                cached_result = None
            
            if should_skip:
                return cached_result
            
            # Analyze tweet content for context
            tweet_context = self._analyze_tweet_context_for_reply(tweet_content)
            
            # Build enhanced prompt for more natural replies
            if custom_prompt:
                prompt = f"""You are a casual Twitter user. Reply to this tweet naturally and briefly.

Tweet: {tweet_content}

Context: {tweet_context}

Custom Instructions: {custom_prompt}

Generate a brief, natural reply ({min_chars}-{max_chars} characters) that:
- Sounds like a real person, not AI
- Uses casual, conversational language
- Uses natural contractions (you're, that's, etc.)
- Avoids overly formal or perfect responses
- Keeps it brief and to the point
- NO hashtags or emojis

Reply:"""
            else:
                prompt = f"""You are a casual Twitter user. Reply to this tweet naturally and briefly.

Tweet: {tweet_content}

Context: {tweet_context}

Generate a brief, natural reply ({min_chars}-{max_chars} characters) that:
- Sounds like a real person, not AI
- Uses casual, conversational language
- Uses natural contractions (you're, that's, etc.)
- Avoids overly formal or perfect responses
- Keeps it brief and to the point
- NO hashtags or emojis

Reply:"""
            
            # Make API call
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a casual Twitter user who replies naturally and briefly. Use conversational language and keep responses between 180-280 characters. No hashtags or emojis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,  # Reduced for brevity
                temperature=0.9,  # Increased for more variety
                top_p=0.95
            )
            
            comment = response.choices[0].message.content.strip()
            
            # Remove any remaining hashtags and emojis
            import re
            comment = re.sub(r'#\w+', '', comment)  # Remove hashtags
            comment = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', comment)  # Remove emojis
            comment = re.sub(r'\s+', ' ', comment).strip()  # Clean whitespace
            
            # Ensure it's within character limit (180-280)
            if len(comment) > 280:
                comment = comment[:280]
            elif len(comment) < 180:
                # If too short, try to expand naturally
                comment = self._expand_short_reply(comment, tweet_content)
            
            # Record successful call (but skip for auto yapping to avoid caching)
            if "[Account:" not in tweet_content and "[Timestamp:" not in tweet_content:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                self._record_successful_call(tweet_content, "tweet_comment", comment, input_tokens, output_tokens)
            
            return comment
            
        except Exception as e:
            self._record_failed_call(str(e))
            log_to_file('ai_integration', f"Error generating comment from tweet: {e}")
            return None
    
    def generate_comment_from_tweet_with_limits(self, tweet_content: str, custom_prompt: str = None, min_chars: int = 180, max_chars: int = 280) -> str:
        """Generate a comment with specific character limits"""
        try:
            # Check if we should skip this call (but disable for auto yapping)
            should_skip, cached_result = self._should_skip_call(tweet_content, "tweet_comment")
            
            # For auto yapping, we want unique replies, so skip caching if content contains unique markers
            if "[Account:" in tweet_content or "[Timestamp:" in tweet_content:
                should_skip = False
                cached_result = None
            
            if should_skip:
                return cached_result
            
            # Analyze tweet content for context
            tweet_context = self._analyze_tweet_context_for_reply(tweet_content)
            
            # Build enhanced prompt for more natural replies
            if custom_prompt:
                prompt = f"""You are a casual Twitter user. Reply to this tweet naturally and briefly.

Tweet: {tweet_content}

Context: {tweet_context}

Custom Instructions: {custom_prompt}

Generate a brief, natural reply ({min_chars}-{max_chars} characters) that:
- Sounds like a real person, not AI
- Uses casual, conversational language
- Uses natural contractions (you're, that's, etc.)
- Avoids overly formal or perfect responses
- Keeps it brief and to the point
- NO hashtags or emojis

Reply:"""
            else:
                prompt = f"""You are a casual Twitter user. Reply to this tweet naturally and briefly.

Tweet: {tweet_content}

Context: {tweet_context}

Generate a brief, natural reply ({min_chars}-{max_chars} characters) that:
- Sounds like a real person, not AI
- Uses casual, conversational language
- Uses natural contractions (you're, that's, etc.)
- Avoids overly formal or perfect responses
- Keeps it brief and to the point
- NO hashtags or emojis

Reply:"""
            
            # Make API call
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a casual Twitter user who replies naturally and briefly. Use conversational language and keep responses between {min_chars}-{max_chars} characters. No hashtags or emojis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,  # Reduced for brevity
                temperature=0.9,  # Increased for more variety
                top_p=0.95
            )
            
            comment = response.choices[0].message.content.strip()
            
            # Remove any remaining hashtags and emojis
            import re
            comment = re.sub(r'#\w+', '', comment)  # Remove hashtags
            comment = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', comment)  # Remove emojis
            comment = re.sub(r'\s+', ' ', comment).strip()  # Clean whitespace
            
            # Ensure it's within character limit
            if len(comment) > max_chars:
                comment = comment[:max_chars]
            elif len(comment) < min_chars:
                # If too short, try to expand naturally
                comment = self._expand_short_reply_with_limits(comment, tweet_content, min_chars, max_chars)
            
            # Record successful call (but skip for auto yapping to avoid caching)
            if "[Account:" not in tweet_content and "[Timestamp:" not in tweet_content:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                self._record_successful_call(tweet_content, "tweet_comment", comment, input_tokens, output_tokens)
            
            return comment
            
        except Exception as e:
            self._record_failed_call(str(e))
            log_to_file('ai_integration', f"Error generating comment from tweet: {e}")
            return None

    def analyze_tweet_context(self, tweet_content: str, comments: List[str] = None) -> Dict:
        """Analyze tweet context and sentiment"""
        if not self.is_configured:
            log_to_file('ai_integration', "OpenAI not configured for analysis, using fallback")
            return self._get_default_analysis()
        
        try:
            # Check if we should skip this call
            content_for_cache = f"{tweet_content}:{comments[:5] if comments else 'no_comments'}"
            skip, cached_result = self._should_skip_call(content_for_cache, "analysis")
            if skip:
                if cached_result:
                    log_to_file('ai_integration', "Using cached analysis result")
                    return json.loads(cached_result)
                else:
                    log_to_file('ai_integration', "Rate limited or budget exceeded for analysis, using fallback")
                    return self._get_default_analysis()
            
            # Use more comments for better context (up to 10 comments)
            comments_text = "\n".join(comments[:10]) if comments else "No comments available"
            
            prompt = f"""
            Analyze this tweet and its context for social media engagement:
            
            Tweet: {tweet_content}
            
            Comments/Replies ({len(comments[:10]) if comments else 0} total):
            {comments_text}
            
            Provide analysis in JSON format with these fields:
            - tweet_sentiment (positive/negative/neutral)
            - context (brief description of what the tweet is about)
            - recommended_response_style (casual/professional/enthusiastic/supportive/humorous)
            - engagement_level (low/medium/high)
            - topic (main topic of the tweet)
            - key_emotions (list of emotions present)
            - audience_tone (how the commenters are responding)
            - viral_potential (low/medium/high)
            """
            
            log_to_file('ai_integration', f"Making OpenAI API call for tweet analysis with {len(comments[:10]) if comments else 0} comments")
            
            # Make API call with retries
            for attempt in range(self.max_retries):
                try:
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a social media analyst. Respond only with valid JSON. Analyze the tweet content and comment context to provide insights for engagement."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=400,
                        temperature=0.3
                    )
                    
                    analysis_text = response.choices[0].message.content.strip()
                    analysis = json.loads(analysis_text)
                    
                    # Record successful call
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    self._record_successful_call(content_for_cache, "analysis", analysis_text, input_tokens, output_tokens)
                    
                    log_to_file('ai_integration', f"Successfully analyzed tweet context with {len(comments[:10]) if comments else 0} comments")
                    return analysis
                    
                except Exception as e:
                    self._record_failed_call(str(e))
                    log_to_file('ai_integration', f"OpenAI API call failed for analysis (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        raise e
            
        except Exception as e:
            log_to_file('ai_integration', f"OpenAI error in analyze_tweet_context: {e}")
            return self._get_default_analysis()
    
    def _build_comment_prompt(self, tweet_content: str, analysis: Dict, custom_prompt: str = None) -> str:
        """Build a context-aware prompt for comment generation"""
        
        # Extract analysis insights
        sentiment = analysis.get('tweet_sentiment', 'neutral')
        context = analysis.get('context', 'general social media post')
        style = analysis.get('recommended_response_style', 'casual')
        engagement = analysis.get('engagement_level', 'medium')
        topic = analysis.get('topic', 'general')
        emotions = analysis.get('key_emotions', [])
        audience_tone = analysis.get('audience_tone', 'neutral')
        
        # Build style-specific instructions
        style_instructions = {
            'casual': 'Use casual, friendly language with emojis and conversational tone',
            'professional': 'Use professional, respectful language with proper grammar',
            'enthusiastic': 'Use excited, energetic language with positive emojis',
            'supportive': 'Use encouraging, supportive language that shows empathy',
            'humorous': 'Use witty, clever language with appropriate humor'
        }
        
        style_guide = style_instructions.get(style, style_instructions['casual'])
        
        # Build the prompt
        prompt = f"""
        Generate ONE engaging comment for this tweet:
        
        Tweet: {tweet_content}
        
        Context Analysis:
        - Sentiment: {sentiment}
        - Topic: {topic}
        - Engagement Level: {engagement}
        - Recommended Style: {style}
        - Key Emotions: {', '.join(emotions) if emotions else 'neutral'}
        - Audience Tone: {audience_tone}
        
        Instructions:
        - {style_guide}
        - Keep it under 100 characters
        - Make it relevant to the tweet content
        - Add value to the conversation
        - Be authentic and engaging
        - Use appropriate emojis if the style allows
        
        Generate ONE high-quality comment:
        """
        
        if custom_prompt:
            prompt += f"\nCustom Instructions: {custom_prompt}"
        
        return prompt
    
    def _get_default_analysis(self) -> Dict:
        """Default analysis when AI is not available"""
        return {
            "tweet_sentiment": "neutral",
            "context": "general social media post",
            "recommended_response_style": "casual",
            "engagement_level": "medium",
            "topic": "general",
            "key_emotions": ["neutral"]
        }
    
    def _should_skip_call(self, content: str, prompt_type: str) -> tuple[bool, Optional[str]]:
        """Check if we should skip this API call"""
        # Check rate limiting
        if not self.rate_limiter.can_make_call():
            log_to_file('ai_integration', "Rate limit exceeded, skipping call")
            return True, None
        
        # Check budget
        estimated_tokens = len(content.split()) * 2  # Rough estimate
        if not self.cost_tracker.can_afford_call(estimated_tokens):
            log_to_file('ai_integration', "Budget exceeded, skipping call")
            return True, None
        
        # Check cache
        cached_result = self.cache.get(content, prompt_type)
        if cached_result:
            log_to_file('ai_integration', "Using cached result")
            return True, cached_result
        
        return False, None
    
    def _record_successful_call(self, content: str, prompt_type: str, result: str, input_tokens: int, output_tokens: int):
        """Record a successful API call"""
        self.rate_limiter.record_call()
        self.cost_tracker.record_cost(input_tokens, output_tokens)
        self.cache.set(content, prompt_type, result)
        log_to_file('ai_integration', f"Successful {prompt_type} call - Input: {input_tokens}, Output: {output_tokens}")
    
    def _record_successful_call_no_cache(self, content: str, prompt_type: str, result: str, input_tokens: int, output_tokens: int):
        """Record a successful API call without caching the result"""
        self.rate_limiter.record_call()
        self.cost_tracker.record_cost(input_tokens, output_tokens)
        # Don't cache comments to ensure fresh generation each time
        log_to_file('ai_integration', f"Successful {prompt_type} call (no cache) - Input: {input_tokens}, Output: {output_tokens}")
    
    def _record_failed_call(self, error: str):
        """Record a failed API call"""
        log_to_file('ai_integration', f"Failed API call: {error}")

    def _analyze_tweet_context_for_reply(self, tweet_content: str) -> str:
        """Analyze tweet content to provide better context for replies"""
        try:
            # Simple context analysis
            content_lower = tweet_content.lower()
            
            # Detect topic/emotion
            if any(word in content_lower for word in ['crypto', 'bitcoin', 'eth', 'trading', 'alpha', 'points']):
                context = "cryptocurrency/trading related"
            elif any(word in content_lower for word in ['ai', 'artificial intelligence', 'machine learning']):
                context = "AI/technology related"
            elif any(word in content_lower for word in ['news', 'announcement', 'update']):
                context = "news/announcement"
            elif any(word in content_lower for word in ['question', 'how', 'what', 'why']):
                context = "question/curiosity"
            elif any(word in content_lower for word in ['great', 'amazing', 'awesome', 'excellent']):
                context = "positive/enthusiastic"
            elif any(word in content_lower for word in ['problem', 'issue', 'bug', 'error']):
                context = "problem/issue"
            else:
                context = "general discussion"
            
            # Detect tone
            if any(word in content_lower for word in ['!', 'wow', 'amazing', 'incredible']):
                tone = "excited/enthusiastic"
            elif any(word in content_lower for word in ['?', 'curious', 'wonder']):
                tone = "curious/questioning"
            elif any(word in content_lower for word in ['sad', 'disappointed', 'frustrated']):
                tone = "concerned/empathetic"
            else:
                tone = "neutral/informative"
            
            return f"Topic: {context}, Tone: {tone}"
            
        except Exception as e:
            return "general discussion"

    def _expand_short_reply(self, short_reply: str, tweet_content: str) -> str:
        """Expand a short reply to meet minimum character requirement"""
        try:
            # Add natural follow-up or question
            if len(short_reply) < 180:
                prompt = f"""The reply "{short_reply}" is too short. Make it longer (180-280 characters) by adding a natural follow-up question or thought. Keep it conversational and brief.

Tweet: {tweet_content}

Current reply: {short_reply}

Expanded reply:"""
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a casual Twitter user. Expand the reply naturally to 180-280 characters."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=80,
                    temperature=0.8
                )
                
                expanded = response.choices[0].message.content.strip()
                
                # Clean and ensure proper length
                import re
                expanded = re.sub(r'#\w+', '', expanded)
                expanded = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', expanded)
                expanded = re.sub(r'\s+', ' ', expanded).strip()
                
                if 180 <= len(expanded) <= 280:
                    return expanded
                else:
                    return short_reply  # Return original if expansion failed
            else:
                return short_reply
                
        except Exception as e:
            return short_reply

    def _expand_short_reply_with_limits(self, short_reply: str, tweet_content: str, min_chars: int, max_chars: int) -> str:
        """Expand a short reply to meet minimum character requirement"""
        try:
            # Add natural follow-up or question
            if len(short_reply) < min_chars:
                prompt = f"""The reply "{short_reply}" is too short. Make it longer ({min_chars}-{max_chars} characters) by adding a natural follow-up question or thought. Keep it conversational and brief.

Tweet: {tweet_content}

Current reply: {short_reply}

Expanded reply:"""
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"You are a casual Twitter user. Expand the reply naturally to {min_chars}-{max_chars} characters."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=80,
                    temperature=0.8
                )
                
                expanded = response.choices[0].message.content.strip()
                
                # Clean and ensure proper length
                import re
                expanded = re.sub(r'#\w+', '', expanded)
                expanded = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', expanded)
                expanded = re.sub(r'\s+', ' ', expanded).strip()
                
                if min_chars <= len(expanded) <= max_chars:
                    return expanded
                else:
                    return short_reply  # Return original if expansion failed
            else:
                return short_reply
                
        except Exception as e:
            return short_reply

    def generate_multiple_reply_styles(self, tweet_content, custom_prompt=None, min_chars=180, max_chars=280):
        """Generate multiple reply styles with enhanced naturalness"""
        try:
            if not tweet_content.strip():
                return ["Interesting tweet! Thanks for sharing."]
            
            # Analyze tweet context
            context_analysis = self._analyze_tweet_context(tweet_content)
            
            # Define personality styles with more natural variations
            styles = [
                {
                    "name": "Casual Expert",
                    "prompt": f"""You're a knowledgeable person in {context_analysis.get('topic', 'tech')}. 
                    Reply naturally with some expertise but keep it casual and conversational. 
                    Share relevant knowledge or experience without being overly technical. Focus on statements and observations."""
                },
                {
                    "name": "Supportive Observer", 
                    "prompt": f"""You're supportive and encouraging. 
                    Acknowledge the value of what they're sharing and show appreciation. 
                    Be positive but genuine, not overly enthusiastic. Make supportive statements."""
                },
                {
                    "name": "Thoughtful Commenter",
                    "prompt": f"""You're thoughtful and reflective. 
                    Share your perspective or make an observation about the broader implications. 
                    Show you've really thought about what they're saying. Focus on insights."""
                },
                {
                    "name": "Engaged Conversationalist",
                    "prompt": f"""You're engaged in the conversation. 
                    Respond naturally as if you're part of an ongoing discussion. 
                    Reference what they said and add to the conversation naturally. Make statements, not questions."""
                },
                {
                    "name": "Enthusiastic Supporter",
                    "prompt": f"""You're genuinely excited about what they're sharing. 
                    Show enthusiasm and appreciation for their content. 
                    Express genuine interest and support. Focus on positive statements."""
                }
            ]
            
            replies = []
            for style in styles:
                try:
                    base_prompt = f"""Generate a natural, human-like reply to this tweet using the {style['name']} style.

Tweet: "{tweet_content}"

Context Analysis:
- Topic: {context_analysis.get('topic', 'general')}
- Tone: {context_analysis.get('tone', 'neutral')}
- Content Type: {context_analysis.get('content_type', 'general')}

Style: {style['prompt']}

Requirements:
- Length: {min_chars}-{max_chars} characters
- Mix of statements, observations, and questions (not just questions)
- Sound natural and genuine, not AI-like
- No hashtags or emojis
- Use casual, conversational tone
- Make it feel like a real person's response
- Vary the response style from other replies"""

                    if custom_prompt:
                        base_prompt += f"\n\nCustom Instructions: {custom_prompt}"
                    
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": f"You are a Twitter user with this personality: {style['prompt']}. Keep replies brief (180-280 characters) and natural."},
                            {"role": "user", "content": base_prompt}
                        ],
                        max_tokens=100,
                        temperature=0.9,
                        top_p=0.95
                    )
                    
                    reply = response.choices[0].message.content.strip()
                    
                    # Clean reply
                    import re
                    reply = re.sub(r'#\w+', '', reply)
                    reply = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', reply)
                    reply = re.sub(r'\s+', ' ', reply).strip()
                    
                    # Ensure proper length
                    if len(reply) > 280:
                        reply = reply[:280]
                    elif len(reply) < 180:
                        reply = self._expand_short_reply(reply, tweet_content)
                    
                    if 180 <= len(reply) <= 280:
                        replies.append(reply)
                        
                except Exception as e:
                    self.logger.error(f"Error generating {style['name']} style: {e}")
                    replies.append("Great tweet! Thanks for sharing.")
            
            return replies if replies else ["Interesting tweet! Thanks for sharing."]
            
        except Exception as e:
            self.logger.error(f"Error generating multiple reply styles: {e}")
            return ["Interesting tweet! Thanks for sharing."]

    # Old method removed - replaced by enhanced generate_comment_from_tweet with better naturalness
    # See line 847 for the enhanced version 

    def generate_comment_from_tweet(self, tweet_content, custom_prompt=None, min_chars=180, max_chars=280):
        """Generate a comment based on tweet content with enhanced naturalness"""
        try:
            # Clean and prepare tweet content
            cleaned_content = tweet_content.strip()
            if not cleaned_content:
                return "Interesting tweet! Thanks for sharing."
            
            # Analyze tweet context for better responses
            context_analysis = self._analyze_tweet_context(cleaned_content)
            
            # Build enhanced prompt with context
            base_prompt = f"""Generate a natural, human-like reply to this tweet. Make it sound genuine and conversational.

Tweet: "{cleaned_content}"

Context Analysis:
- Topic: {context_analysis.get('topic', 'general')}
- Tone: {context_analysis.get('tone', 'neutral')}
- Content Type: {context_analysis.get('content_type', 'general')}

Requirements:
- Length: {min_chars}-{max_chars} characters
- Focus on statements, observations, and insights (avoid questions)
- Sound natural and genuine, not AI-like
- No hashtags or emojis
- Show genuine interest or knowledge about the topic
- Use casual, conversational tone
- Include personal perspective or experience when relevant
- Make it feel like a real person's response

Response styles to choose from:
1. Share similar experience or knowledge
2. Make an observation or insight
3. Express genuine interest or excitement
4. Offer perspective or opinion
5. Connect to broader context or trends
6. Show appreciation or support

Choose the most natural style based on the tweet content. Focus on making statements, not asking questions."""

            if custom_prompt:
                base_prompt += f"\n\nCustom Instructions: {custom_prompt}"
            
            # Add unique marker to bypass cache for auto yapping
            if '[Account:' in tweet_content or '[Timestamp:' in tweet_content:
                base_prompt += f"\n\nUnique Context: {tweet_content[:100]}..."
            
            response = self._make_openai_call(base_prompt, max_tokens=150)
            
            if response:
                # Clean and validate response
                cleaned_response = self._clean_ai_response(response)
                
                # Ensure character limit
                if len(cleaned_response) > max_chars:
                    cleaned_response = cleaned_response[:max_chars-3] + "..."
                elif len(cleaned_response) < min_chars:
                    # Expand short responses naturally
                    cleaned_response = self._expand_short_response(cleaned_response, min_chars)
                
                return cleaned_response
            
            return "Interesting perspective! Thanks for sharing."
            
        except Exception as e:
            log_to_file('ai_integration', f"Error generating comment: {e}")
            return "Great tweet! Thanks for sharing."

    def _analyze_tweet_context(self, tweet_content):
        """Analyze tweet content for better context-aware responses"""
        content_lower = tweet_content.lower()
        
        # Topic detection
        topics = {
            'crypto': ['crypto', 'bitcoin', 'eth', 'blockchain', 'defi', 'nft', 'token', 'wallet'],
            'tech': ['ai', 'machine learning', 'software', 'app', 'development', 'code', 'programming'],
            'finance': ['money', 'investment', 'trading', 'profit', 'market', 'stock', 'portfolio'],
            'business': ['startup', 'company', 'entrepreneur', 'business', 'product', 'service'],
            'personal': ['life', 'experience', 'journey', 'story', 'personal', 'family'],
            'news': ['news', 'update', 'announcement', 'release', 'launch']
        }
        
        detected_topic = 'general'
        for topic, keywords in topics.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_topic = topic
                break
        
        # Tone detection
        tone_indicators = {
            'excited': ['amazing', 'incredible', 'awesome', 'wow', 'fantastic', 'great'],
            'concerned': ['worried', 'concerned', 'issue', 'problem', 'challenge'],
            'curious': ['wonder', 'curious', 'interesting', 'fascinating'],
            'confident': ['sure', 'confident', 'definitely', 'certainly'],
            'neutral': ['update', 'news', 'information', 'data']
        }
        
        detected_tone = 'neutral'
        for tone, indicators in tone_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                detected_tone = tone
                break
        
        # Content type detection
        content_types = {
            'question': ['?', 'how', 'what', 'why', 'when', 'where'],
            'announcement': ['launch', 'release', 'announce', 'introduce'],
            'opinion': ['think', 'believe', 'feel', 'opinion', 'view'],
            'experience': ['experience', 'journey', 'story', 'happened'],
            'information': ['data', 'stats', 'numbers', 'results', 'update']
        }
        
        detected_type = 'general'
        for content_type, indicators in content_types.items():
            if any(indicator in content_lower for indicator in indicators):
                detected_type = content_type
                break
        
        return {
            'topic': detected_topic,
            'tone': detected_tone,
            'content_type': detected_type
        }

    def _clean_ai_response(self, response):
        """Clean AI response to make it more natural"""
        # Remove common AI artifacts
        response = response.strip()
        
        # Remove quotes if they wrap the entire response
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        # Remove hashtags and emojis
        import re
        response = re.sub(r'#[A-Za-z0-9_]+', '', response)  # Remove hashtags
        response = re.sub(r'[^\x00-\x7F]+', '', response)   # Remove emojis
        
        # Clean up extra spaces
        response = re.sub(r'\s+', ' ', response).strip()
        
        return response

    def _expand_short_response(self, response, min_chars):
        """Expand short responses naturally"""
        if len(response) >= min_chars:
            return response
        
        # Add natural extensions based on response type (avoid questions)
        if any(word in response.lower() for word in ['interesting', 'fascinating', 'amazing']):
            # For positive reactions, add engagement
            extensions = [
                " Thanks for sharing this insight.",
                " Appreciate you bringing this up.",
                " This is really valuable information.",
                " Great to see this perspective."
            ]
        elif any(word in response.lower() for word in ['think', 'believe', 'feel']):
            # For opinion-based responses, add context
            extensions = [
                " That's a really good point.",
                " I appreciate your perspective on this.",
                " That makes a lot of sense.",
                " Thanks for sharing your thoughts."
            ]
        else:
            # For general responses, add natural follow-up
            extensions = [
                " Thanks for sharing this.",
                " Appreciate the update.",
                " Good to know about this.",
                " Thanks for the information."
            ]
        
        import random
        extension = random.choice(extensions)
        expanded = response + extension
        
        # Ensure we don't exceed max chars
        if len(expanded) > 280:
            return response  # Return original if expansion would be too long
        
        return expanded

    def _make_openai_call(self, prompt, max_tokens=150):
        """Make OpenAI API call with error handling"""
        try:
            if not client:
                return None
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a casual Twitter user who creates natural, engaging replies. Be conversational and genuine. Focus on making statements and observations, avoid asking questions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.8,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log_to_file('ai_integration', f"OpenAI API call failed: {e}")
            return None


class AIIntegrationManager:
    """Manages OpenAI integration with fallback"""
    
    def __init__(self):
        self.provider = None
        self._load_provider()
    
    def _load_provider(self):
        """Load OpenAI provider"""
        openai_key = os.getenv('OPENAI_API_KEY')
        log_to_file('ai_integration', f"Loading OpenAI provider - API key: {'Yes' if openai_key else 'No'}")
        
        self.provider = OpenAIProvider(openai_key)
        log_to_file('ai_integration', f"OpenAI provider initialized: {self.provider.is_configured}")
    
    def set_provider(self, provider_name: str) -> bool:
        """Set the active AI provider (only OpenAI supported)"""
        if provider_name == 'openai':
            log_to_file('ai_integration', "Provider set to OpenAI")
            return True
        else:
            log_to_file('ai_integration', f"Provider {provider_name} not supported, using OpenAI")
            return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return ['openai']
    
    def get_current_provider_info(self) -> Dict:
        """Get info about current provider"""
        if not self.provider:
            return {"name": "None", "configured": False}
        
        return {
            "name": self.provider.name,
            "configured": self.provider.is_configured
        }
    
    def generate_comment(self, tweet_content: str, analysis: Dict, custom_prompt: str = None) -> str:
        """Generate comment using OpenAI"""
        if not self.provider:
            return "Great post! Thanks for sharing."
        
        return self.provider.generate_comment(tweet_content, analysis, custom_prompt)
    
    def analyze_tweet_context(self, tweet_content: str, comments: List[str] = None) -> Dict:
        """Analyze tweet context using OpenAI"""
        if not self.provider:
            return self._get_default_analysis()
        
        return self.provider.analyze_tweet_context(tweet_content, comments)
    
    def generate_comment_from_tweet(self, tweet_content, custom_prompt=None, min_chars=180, max_chars=280):
        """Generate a comment based on tweet content with enhanced naturalness"""
        if self.provider:
            return self.provider.generate_comment_from_tweet(tweet_content, custom_prompt, min_chars, max_chars)
        return "Great tweet! Thanks for sharing."
    
    def _get_default_analysis(self) -> Dict:
        """Default analysis when AI is not available"""
        return {
            "tweet_sentiment": "neutral",
            "context": "general social media post",
            "recommended_response_style": "casual",
            "engagement_level": "medium",
            "topic": "general",
            "key_emotions": ["neutral"]
        }


def create_ai_integration() -> AIIntegrationManager:
    """Create and return AI integration manager"""
    return AIIntegrationManager() 