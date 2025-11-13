"""
Sentiment Analyzer Plugin Example
Demonstrates how to create a custom agent plugin for Manus AI
"""

from manus_ai.core.plugin_system import BaseAgent
from typing import Dict, Any
import re

__version__ = "1.0.0"
__author__ = "Manus AI Team"
__dependencies__ = []
__tags__ = ["nlp", "sentiment", "analysis"]

PLUGIN_METADATA = {
    "name": "SentimentAnalyzer",
    "version": "1.0.0",
    "author": "Manus AI Team",
    "description": "Analyzes sentiment of text using rule-based and keyword matching",
    "capabilities": [
        "Sentiment classification (positive/negative/neutral)",
        "Emotion detection (joy, sadness, anger, fear, etc.)",
        "Confidence scoring",
        "Batch text analysis",
        "Detailed sentiment breakdown"
    ],
    "dependencies": [],
    "config_schema": {
        "confidence_threshold": {
            "type": "float",
            "default": 0.6,
            "description": "Minimum confidence threshold for classification"
        },
        "enable_emotions": {
            "type": "boolean",
            "default": True,
            "description": "Enable emotion detection"
        }
    },
    "tags": ["nlp", "sentiment", "analysis", "text"]
}


class SentimentAnalyzer(BaseAgent):
    """
    Custom agent for sentiment analysis

    This plugin demonstrates:
    - Proper plugin structure
    - Configuration handling
    - Error handling
    - Result formatting
    - Multiple analysis modes
    """

    # Sentiment lexicons
    POSITIVE_WORDS = {
        'excellent', 'amazing', 'wonderful', 'fantastic', 'great', 'good',
        'love', 'best', 'perfect', 'beautiful', 'happy', 'joy', 'delighted',
        'pleased', 'satisfied', 'awesome', 'brilliant', 'superb', 'outstanding',
        'exceptional', 'marvelous', 'magnificent', 'terrific', 'splendid'
    }

    NEGATIVE_WORDS = {
        'terrible', 'awful', 'horrible', 'bad', 'worst', 'hate', 'disgusting',
        'disappointing', 'poor', 'sad', 'angry', 'frustrated', 'annoying',
        'useless', 'pathetic', 'dreadful', 'appalling', 'atrocious', 'inferior',
        'mediocre', 'unsatisfactory', 'inadequate', 'deficient'
    }

    INTENSIFIERS = {
        'very', 'extremely', 'absolutely', 'completely', 'totally',
        'really', 'incredibly', 'exceptionally', 'remarkably'
    }

    NEGATIONS = {
        'not', 'no', 'never', 'neither', 'nobody', 'nothing',
        "n't", "dont", "doesnt", "didnt", "wont", "cant"
    }

    EMOTIONS = {
        'joy': {'happy', 'joy', 'delighted', 'cheerful', 'ecstatic', 'elated'},
        'sadness': {'sad', 'depressed', 'miserable', 'gloomy', 'melancholy'},
        'anger': {'angry', 'furious', 'enraged', 'mad', 'irritated', 'annoyed'},
        'fear': {'afraid', 'scared', 'terrified', 'anxious', 'worried', 'nervous'},
        'surprise': {'surprised', 'amazed', 'astonished', 'shocked', 'stunned'},
        'disgust': {'disgusting', 'revolting', 'repulsive', 'gross', 'nasty'}
    }

    def __init__(self):
        super().__init__()
        self.name = "SentimentAnalyzer"
        self.description = "Analyzes sentiment and emotions in text"
        self.capabilities = PLUGIN_METADATA["capabilities"]

        # Configuration
        self.confidence_threshold = 0.6
        self.enable_emotions = True

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration"""
        try:
            self.confidence_threshold = config.get('confidence_threshold', 0.6)
            self.enable_emotions = config.get('enable_emotions', True)

            self.logger.info(
                f"Initialized {self.name} - "
                f"threshold: {self.confidence_threshold}, "
                f"emotions: {self.enable_emotions}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute sentiment analysis

        Args:
            task: Dictionary with:
                - text: str - Text to analyze (required)
                - mode: str - Analysis mode ('simple', 'detailed', 'batch')
                - texts: List[str] - For batch mode

        Returns:
            Dictionary with analysis results
        """
        try:
            mode = task.get('mode', 'simple')

            if mode == 'batch':
                return await self._analyze_batch(task.get('texts', []))
            else:
                text = task.get('text', '')
                if not text:
                    return {
                        "status": "error",
                        "agent": self.name,
                        "error": "No text provided",
                        "message": "Text is required for analysis"
                    }

                result = await self._analyze_text(text, detailed=(mode == 'detailed'))

                return {
                    "status": "success",
                    "agent": self.name,
                    "result": result,
                    "message": f"Sentiment: {result['sentiment']} ({result['confidence']:.1%})"
                }

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return {
                "status": "error",
                "agent": self.name,
                "error": str(e),
                "message": f"Sentiment analysis failed: {e}"
            }

    async def _analyze_text(self, text: str, detailed: bool = False) -> Dict[str, Any]:
        """Analyze single text"""
        # Tokenize
        words = self._tokenize(text)

        # Calculate sentiment scores
        positive_score = 0
        negative_score = 0

        for i, word in enumerate(words):
            word_lower = word.lower()

            # Check for negation in previous words
            negated = any(words[max(0, i-2):i]) in self.NEGATIONS for w in words[max(0, i-2):i])

            # Check for intensifier in previous words
            intensified = any(w.lower() in self.INTENSIFIERS for w in words[max(0, i-2):i])
            multiplier = 1.5 if intensified else 1.0

            # Score positive words
            if word_lower in self.POSITIVE_WORDS:
                score = multiplier
                if negated:
                    negative_score += score
                else:
                    positive_score += score

            # Score negative words
            elif word_lower in self.NEGATIVE_WORDS:
                score = multiplier
                if negated:
                    positive_score += score
                else:
                    negative_score += score

        # Determine sentiment
        total = positive_score + negative_score
        if total == 0:
            sentiment = "neutral"
            confidence = 0.5
        else:
            pos_ratio = positive_score / total
            if pos_ratio > 0.6:
                sentiment = "positive"
                confidence = pos_ratio
            elif pos_ratio < 0.4:
                sentiment = "negative"
                confidence = 1 - pos_ratio
            else:
                sentiment = "neutral"
                confidence = 0.5 + abs(0.5 - pos_ratio)

        result = {
            "text": text,
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_score": positive_score,
            "negative_score": negative_score,
            "word_count": len(words)
        }

        # Add detailed analysis
        if detailed:
            result["emotions"] = await self._detect_emotions(words) if self.enable_emotions else {}
            result["keywords"] = self._extract_sentiment_keywords(words)
            result["sentence_sentiments"] = await self._analyze_sentences(text)

        return result

    async def _analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze multiple texts"""
        results = []

        for text in texts:
            analysis = await self._analyze_text(text, detailed=False)
            results.append(analysis)

        # Aggregate statistics
        sentiments = [r['sentiment'] for r in results]
        avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0

        return {
            "status": "success",
            "agent": self.name,
            "results": results,
            "summary": {
                "total": len(results),
                "positive": sentiments.count('positive'),
                "negative": sentiments.count('negative'),
                "neutral": sentiments.count('neutral'),
                "average_confidence": avg_confidence
            }
        }

    async def _detect_emotions(self, words: List[str]) -> Dict[str, float]:
        """Detect emotions in text"""
        emotions = {}

        for emotion, keywords in self.EMOTIONS.items():
            matches = sum(1 for w in words if w.lower() in keywords)
            if matches > 0:
                emotions[emotion] = min(matches / len(words) * 10, 1.0)

        return emotions

    def _extract_sentiment_keywords(self, words: List[str]) -> Dict[str, List[str]]:
        """Extract sentiment-bearing keywords"""
        positive = [w for w in words if w.lower() in self.POSITIVE_WORDS]
        negative = [w for w in words if w.lower() in self.NEGATIVE_WORDS]

        return {
            "positive": positive,
            "negative": negative
        }

    async def _analyze_sentences(self, text: str) -> List[Dict[str, Any]]:
        """Analyze sentiment for each sentence"""
        sentences = re.split(r'[.!?]+', text)
        results = []

        for sentence in sentences:
            if sentence.strip():
                analysis = await self._analyze_text(sentence.strip())
                results.append({
                    "sentence": sentence.strip(),
                    "sentiment": analysis['sentiment'],
                    "confidence": analysis['confidence']
                })

        return results

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.split()

    def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate task parameters"""
        mode = task.get('mode', 'simple')

        if mode == 'batch':
            return 'texts' in task and isinstance(task['texts'], list)
        else:
            return 'text' in task and isinstance(task['text'], str)

    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info(f"Cleaning up {self.name}")
        # No cleanup needed for this simple plugin


# Example usage when run directly
async def demo():
    """Demonstrate plugin usage"""
    plugin = SentimentAnalyzer()
    await plugin.initialize({'confidence_threshold': 0.6})

    # Test cases
    tests = [
        "This product is absolutely amazing! I love it!",
        "Terrible experience. Very disappointed and angry.",
        "It's okay, nothing special.",
        "The service was not bad, but could be better."
    ]

    print("Sentiment Analysis Plugin Demo\n")
    print("=" * 60)

    for text in tests:
        result = await plugin.execute({'text': text, 'mode': 'detailed'})

        if result['status'] == 'success':
            r = result['result']
            print(f"\nText: \"{text}\"")
            print(f"Sentiment: {r['sentiment'].upper()}")
            print(f"Confidence: {r['confidence']:.1%}")
            print(f"Scores: +{r['positive_score']:.1f} / -{r['negative_score']:.1f}")

            if r.get('emotions'):
                print(f"Emotions: {', '.join(f'{k}({v:.1%})' for k, v in r['emotions'].items())}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
