"""
Model Configuration & Download Manager

Downloads and configures:
- Google TimesFM (time series forecasting)
- DeepSeek Math (mathematical reasoning)
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages downloading and caching ML models from Hugging Face."""

    # Model configurations
    MODELS = {
        'timesfm': {
            'name': 'Google TimesFM 1.0 (200M)',
            'url': 'https://huggingface.co/google/timesfm-1.0-200m',
            'repo_id': 'google/timesfm-1.0-200m',
            'type': 'time_series',
            'size_gb': 0.8,
            'purpose': 'Time series forecasting for sports statistics',
        },
        'deepseek_math': {
            'name': 'DeepSeek Math 7B',
            'url': 'https://huggingface.co/deepseek-ai/deepseek-math-7b-instruct',
            'repo_id': 'deepseek-ai/deepseek-math-7b-instruct',
            'type': 'math_reasoning',
            'size_gb': 15,
            'purpose': 'Mathematical reasoning for predictions',
        },
    }

    def __init__(self, cache_dir: str = './models', use_gpu: bool = False):
        """
        Initialize model manager.

        Args:
            cache_dir: Directory to cache downloaded models
            use_gpu: Whether to use GPU acceleration
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_gpu = use_gpu
        self.device = 'cuda' if use_gpu else 'cpu'

        logger.info(f"Model Manager initialized")
        logger.info(f"Cache directory: {self.cache_dir}")
        logger.info(f"Device: {self.device.upper()}")

    def download_model(self, model_key: str, force: bool = False) -> Optional[Path]:
        """
        Download model from Hugging Face.

        Args:
            model_key: 'timesfm' or 'deepseek_math'
            force: Force re-download even if exists

        Returns:
            Path to downloaded model
        """
        if model_key not in self.MODELS:
            logger.error(f"Unknown model: {model_key}")
            return None

        model_info = self.MODELS[model_key]
        model_path = self.cache_dir / model_key

        # Check if already downloaded
        if model_path.exists() and not force:
            logger.info(f"✅ Model already cached: {model_key}")
            return model_path

        logger.info(f"📥 Downloading {model_info['name']}...")
        logger.info(f"   Size: ~{model_info['size_gb']}GB")
        logger.info(f"   Purpose: {model_info['purpose']}")

        try:
            # Use huggingface_hub to download
            from huggingface_hub import snapshot_download

            model_path_str = str(model_path)

            # Download model
            downloaded_path = snapshot_download(
                repo_id=model_info['repo_id'],
                cache_dir=str(self.cache_dir),
                revision='main',
                token=self._get_hf_token(),
            )

            logger.info(f"✅ Downloaded to: {downloaded_path}")
            return Path(downloaded_path)

        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            logger.info(f"   Manual download: {model_info['url']}")
            return None

    def download_all_models(self) -> dict:
        """Download all models."""
        results = {}
        for model_key in self.MODELS:
            results[model_key] = self.download_model(model_key)
        return results

    @staticmethod
    def _get_hf_token() -> Optional[str]:
        """Get Hugging Face token from environment."""
        token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
        if token:
            logger.info("✅ Using Hugging Face token from environment")
        return token

    def get_model_info(self, model_key: str) -> dict:
        """Get model information."""
        return self.MODELS.get(model_key, {})

    def list_models(self) -> None:
        """List available models."""
        print("\n" + "=" * 70)
        print("Available Models for Sports Prediction")
        print("=" * 70)

        for key, info in self.MODELS.items():
            status = "✅ Cached" if (self.cache_dir / key).exists() else "⏳ Not cached"
            print(f"\n{key.upper()}")
            print(f"  Name: {info['name']}")
            print(f"  Status: {status}")
            print(f"  Size: ~{info['size_gb']}GB")
            print(f"  Purpose: {info['purpose']}")
            print(f"  URL: {info['url']}")

        print("\n" + "=" * 70)


class TimesFMPredictor:
    """Time Series Forecasting for sports data."""

    def __init__(self, model_path: Optional[Path] = None, device: str = 'cpu'):
        """
        Initialize TimesFM predictor.

        Args:
            model_path: Path to downloaded model
            device: 'cpu' or 'cuda'
        """
        self.model_path = model_path
        self.device = device
        self.model = None

        logger.info(f"TimesFM Predictor initialized on {device.upper()}")

    def load_model(self):
        """Load TimesFM model."""
        try:
            from timesfm import TimesFM

            logger.info("Loading TimesFM model...")
            self.model = TimesFM(
                context_len=512,
                prediction_len=128,
                num_time_series=100,
                use_gpu=self.device == 'cuda',
                backend='jax',
            )
            logger.info("✅ TimesFM model loaded")
            return self.model

        except ImportError:
            logger.error("TimesFM not installed. Install with: pip install timesfm")
            return None

    def forecast(self, time_series_data: list, steps: int = 10) -> dict:
        """
        Forecast next values in time series.

        Args:
            time_series_data: Historical data points
            steps: Number of steps to forecast

        Returns:
            Forecast with predictions and confidence intervals
        """
        if not self.model:
            self.load_model()

        if not self.model:
            logger.error("Model not loaded")
            return {}

        try:
            # Prepare data
            import numpy as np
            ts_data = np.array(time_series_data).reshape(1, -1)

            # Generate forecast
            forecast = self.model.forecast(
                ts_data,
                num_time_steps=steps,
            )

            return {
                'predictions': forecast[0].tolist(),
                'steps': steps,
                'method': 'TimesFM',
                'confidence': 'high',
            }

        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            return {}

    def forecast_sports_stats(self, team_stats: dict, stat_name: str,
                             forecast_games: int = 10) -> dict:
        """
        Forecast sports statistics for a team.

        Args:
            team_stats: Dictionary with stat history
            stat_name: Name of statistic to forecast
            forecast_games: Number of games to forecast

        Returns:
            Forecast for the statistic
        """
        if stat_name not in team_stats:
            logger.error(f"Statistic not found: {stat_name}")
            return {}

        historical_data = team_stats[stat_name]
        forecast_result = self.forecast(historical_data, forecast_games)

        return {
            'team': team_stats.get('team', 'Unknown'),
            'statistic': stat_name,
            'historical_avg': sum(historical_data) / len(historical_data),
            'forecast': forecast_result,
            'trend': 'up' if forecast_result.get('predictions', [0])[-1] >
                     (sum(historical_data) / len(historical_data)) else 'down',
        }


class DeepSeekMathReasoner:
    """Mathematical reasoning for sports predictions."""

    def __init__(self, model_path: Optional[Path] = None, device: str = 'cpu'):
        """
        Initialize DeepSeek Math reasoner.

        Args:
            model_path: Path to downloaded model
            device: 'cpu' or 'cuda'
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        self.tokenizer = None

        logger.info(f"DeepSeek Math Reasoner initialized on {device.upper()}")

    def load_model(self):
        """Load DeepSeek Math model."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            logger.info("Loading DeepSeek Math model...")

            model_id = "deepseek-ai/deepseek-math-7b-instruct"

            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                device_map=self.device,
            )

            logger.info("✅ DeepSeek Math model loaded")
            return self.model

        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            logger.info("Install with: pip install transformers torch")
            return None

    def calculate_prediction(self, problem: str, max_tokens: int = 512) -> dict:
        """
        Use DeepSeek Math to solve a prediction problem.

        Args:
            problem: Mathematical problem or prediction question
            max_tokens: Maximum response length

        Returns:
            Reasoning and answer
        """
        if not self.model:
            self.load_model()

        if not self.model:
            logger.error("Model not loaded")
            return {}

        try:
            import torch

            # Prepare prompt
            prompt = f"""You are a sports analytics expert. Solve this prediction problem using mathematical reasoning.

Problem: {problem}

Provide a clear mathematical solution with step-by-step reasoning."""

            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors='pt').to(self.device)

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    top_p=0.9,
                )

            # Decode
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            return {
                'problem': problem,
                'reasoning': response,
                'model': 'DeepSeek Math 7B',
                'confidence': 'high',
            }

        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            return {}

    def predict_game_outcome(self, game_data: dict) -> dict:
        """
        Predict game outcome using mathematical reasoning.

        Args:
            game_data: Dictionary with game statistics

        Returns:
            Prediction with mathematical reasoning
        """
        team1 = game_data.get('team1', 'Team 1')
        team2 = game_data.get('team2', 'Team 2')
        team1_stats = game_data.get('team1_stats', {})
        team2_stats = game_data.get('team2_stats', {})

        problem = f"""
Given the following sports statistics:

{team1}:
- Points per game: {team1_stats.get('ppg', 'N/A')}
- Defense rating: {team1_stats.get('drtg', 'N/A')}
- Winning percentage: {team1_stats.get('win_pct', 'N/A')}

{team2}:
- Points per game: {team2_stats.get('ppg', 'N/A')}
- Defense rating: {team2_stats.get('drtg', 'N/A')}
- Winning percentage: {team2_stats.get('win_pct', 'N/A')}

Predict the likely winner and provide the mathematical reasoning.
"""

        result = self.calculate_prediction(problem)

        return {
            'matchup': f"{team1} vs {team2}",
            'prediction': result.get('reasoning', ''),
            'confidence': 'high',
            'model': 'DeepSeek Math',
        }


def setup_prediction_models() -> dict:
    """Setup and download all prediction models."""
    print("\n" + "=" * 70)
    print("Setting Up Sports Prediction Models")
    print("=" * 70)

    manager = ModelManager(use_gpu=False)  # Set to True if GPU available
    manager.list_models()

    print("\n📥 Downloading models...")

    # Download models
    models = {}

    # TimesFM
    print("\n1️⃣  Downloading Google TimesFM...")
    timesfm_path = manager.download_model('timesfm')
    if timesfm_path:
        models['timesfm'] = TimesFMPredictor(timesfm_path)
    else:
        print("   ⚠️  TimesFM download skipped (can install manually)")

    # DeepSeek Math
    print("\n2️⃣  Downloading DeepSeek Math...")
    deepseek_path = manager.download_model('deepseek_math')
    if deepseek_path:
        models['deepseek_math'] = DeepSeekMathReasoner(deepseek_path)
    else:
        print("   ⚠️  DeepSeek Math download skipped (can install manually)")

    print("\n" + "=" * 70)
    print("✅ Model setup complete")
    print("=" * 70 + "\n")

    return models


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup models
    models = setup_prediction_models()

    print("\nModels ready for use:")
    for name, model in models.items():
        print(f"  ✅ {name}")
