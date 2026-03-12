"""
Keras Integration for ag3ntwerk.

Provides deep learning capabilities using Keras/TensorFlow.
Enables custom model training, inference, and embeddings.

Requirements:
    - pip install tensorflow keras

Keras is ideal for:
    - Custom classification models for task routing
    - Sentiment analysis for agent communication
    - Document embedding and similarity
    - Time series forecasting for business metrics
    - Custom NLP models for domain-specific tasks
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Types of models supported."""

    CLASSIFIER = "classifier"
    REGRESSOR = "regressor"
    EMBEDDING = "embedding"
    SEQUENCE = "sequence"
    ENCODER_DECODER = "encoder_decoder"
    TRANSFORMER = "transformer"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for a Keras model."""

    name: str
    model_type: ModelType = ModelType.CLASSIFIER
    input_shape: Optional[Tuple[int, ...]] = None
    output_shape: Optional[Tuple[int, ...]] = None
    num_classes: Optional[int] = None
    vocab_size: Optional[int] = None
    embedding_dim: int = 128
    hidden_units: List[int] = field(default_factory=lambda: [256, 128])
    dropout_rate: float = 0.2
    activation: str = "relu"
    output_activation: str = "softmax"
    use_batch_norm: bool = True
    l2_regularization: float = 0.01


@dataclass
class TrainingConfig:
    """Configuration for model training."""

    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 0.001
    optimizer: str = "adam"
    loss: str = "categorical_crossentropy"
    metrics: List[str] = field(default_factory=lambda: ["accuracy"])
    validation_split: float = 0.2
    early_stopping_patience: int = 3
    reduce_lr_patience: int = 2
    checkpoint_path: Optional[str] = None
    tensorboard_log_dir: Optional[str] = None


class KerasIntegration:
    """
    Integration with Keras for deep learning capabilities.

    Provides model building, training, and inference for ag3ntwerk.

    Example:
        integration = KerasIntegration()

        # Create a text classifier
        model = integration.create_text_classifier(
            vocab_size=10000,
            num_classes=5,
            name="task_classifier",
        )

        # Train the model
        history = integration.train(
            model,
            train_data=(X_train, y_train),
            config=TrainingConfig(epochs=10),
        )

        # Make predictions
        predictions = integration.predict(model, X_test)
    """

    def __init__(
        self,
        models_dir: Optional[str] = None,
        use_gpu: bool = True,
    ):
        """
        Initialize Keras integration.

        Args:
            models_dir: Directory to save/load models
            use_gpu: Whether to use GPU if available
        """
        self.models_dir = Path(models_dir) if models_dir else Path("./models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.use_gpu = use_gpu
        self._models: Dict[str, Any] = {}
        self._tf = None
        self._keras = None

        self._configure_backend()

    def _configure_backend(self) -> None:
        """Configure TensorFlow/Keras backend."""
        if not self.use_gpu:
            os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    def _get_keras(self):
        """Lazy load Keras."""
        if self._keras is None:
            try:
                import keras

                self._keras = keras
            except ImportError:
                try:
                    from tensorflow import keras

                    self._keras = keras
                except ImportError:
                    raise ImportError(
                        "Keras not installed. Install with: pip install keras tensorflow"
                    )
        return self._keras

    def _get_tf(self):
        """Lazy load TensorFlow."""
        if self._tf is None:
            try:
                import tensorflow as tf

                self._tf = tf
            except ImportError:
                raise ImportError("TensorFlow not installed. Install with: pip install tensorflow")
        return self._tf

    def create_text_classifier(
        self,
        vocab_size: int,
        num_classes: int,
        max_length: int = 256,
        embedding_dim: int = 128,
        name: str = "text_classifier",
    ) -> Any:
        """
        Create a text classification model.

        Args:
            vocab_size: Size of vocabulary
            num_classes: Number of output classes
            max_length: Maximum sequence length
            embedding_dim: Embedding dimension
            name: Model name

        Returns:
            Keras model
        """
        keras = self._get_keras()

        model = keras.Sequential(
            [
                keras.layers.Embedding(
                    vocab_size,
                    embedding_dim,
                    input_length=max_length,
                ),
                keras.layers.Bidirectional(keras.layers.LSTM(64, return_sequences=True)),
                keras.layers.Bidirectional(keras.layers.LSTM(32)),
                keras.layers.Dense(64, activation="relu"),
                keras.layers.Dropout(0.3),
                keras.layers.Dense(num_classes, activation="softmax"),
            ],
            name=name,
        )

        self._models[name] = model
        return model

    def create_embedding_model(
        self,
        vocab_size: int,
        embedding_dim: int = 256,
        max_length: int = 512,
        name: str = "embedding_model",
    ) -> Any:
        """
        Create a text embedding model.

        Args:
            vocab_size: Size of vocabulary
            embedding_dim: Output embedding dimension
            max_length: Maximum sequence length
            name: Model name

        Returns:
            Keras model
        """
        keras = self._get_keras()

        inputs = keras.layers.Input(shape=(max_length,))
        x = keras.layers.Embedding(vocab_size, embedding_dim)(inputs)
        x = keras.layers.Bidirectional(keras.layers.LSTM(128, return_sequences=True))(x)
        x = keras.layers.GlobalAveragePooling1D()(x)
        x = keras.layers.Dense(embedding_dim, activation="tanh")(x)
        outputs = keras.layers.Lambda(lambda x: keras.backend.l2_normalize(x, axis=1))(x)

        model = keras.Model(inputs=inputs, outputs=outputs, name=name)
        self._models[name] = model
        return model

    def create_sentiment_analyzer(
        self,
        vocab_size: int,
        max_length: int = 128,
        name: str = "sentiment_analyzer",
    ) -> Any:
        """
        Create a sentiment analysis model (positive/negative/neutral).

        Args:
            vocab_size: Size of vocabulary
            max_length: Maximum sequence length
            name: Model name

        Returns:
            Keras model
        """
        return self.create_text_classifier(
            vocab_size=vocab_size,
            num_classes=3,  # positive, negative, neutral
            max_length=max_length,
            name=name,
        )

    def create_task_router(
        self,
        vocab_size: int,
        num_executives: int,
        max_length: int = 256,
        name: str = "task_router",
    ) -> Any:
        """
        Create a model to route tasks to appropriate agents.

        Args:
            vocab_size: Size of vocabulary
            num_executives: Number of agent types to route to
            max_length: Maximum task description length
            name: Model name

        Returns:
            Keras model
        """
        keras = self._get_keras()

        inputs = keras.layers.Input(shape=(max_length,))

        # Text encoding branch
        x = keras.layers.Embedding(vocab_size, 128)(inputs)
        x = keras.layers.Conv1D(128, 5, activation="relu")(x)
        x = keras.layers.MaxPooling1D(2)(x)
        x = keras.layers.Conv1D(64, 3, activation="relu")(x)
        x = keras.layers.GlobalMaxPooling1D()(x)

        # Classification head
        x = keras.layers.Dense(128, activation="relu")(x)
        x = keras.layers.Dropout(0.3)(x)
        x = keras.layers.Dense(64, activation="relu")(x)
        outputs = keras.layers.Dense(num_executives, activation="softmax")(x)

        model = keras.Model(inputs=inputs, outputs=outputs, name=name)
        self._models[name] = model
        return model

    def create_time_series_forecaster(
        self,
        input_features: int,
        output_steps: int,
        sequence_length: int = 60,
        name: str = "forecaster",
    ) -> Any:
        """
        Create a time series forecasting model.

        Args:
            input_features: Number of input features
            output_steps: Number of steps to forecast
            sequence_length: Input sequence length
            name: Model name

        Returns:
            Keras model
        """
        keras = self._get_keras()

        model = keras.Sequential(
            [
                keras.layers.LSTM(
                    64,
                    return_sequences=True,
                    input_shape=(sequence_length, input_features),
                ),
                keras.layers.LSTM(32),
                keras.layers.Dense(32, activation="relu"),
                keras.layers.Dense(output_steps),
            ],
            name=name,
        )

        self._models[name] = model
        return model

    def create_custom_model(
        self,
        config: ModelConfig,
    ) -> Any:
        """
        Create a custom model from configuration.

        Args:
            config: Model configuration

        Returns:
            Keras model
        """
        keras = self._get_keras()

        if config.model_type == ModelType.CLASSIFIER:
            layers = [keras.layers.Input(shape=config.input_shape)]

            for units in config.hidden_units:
                layers.append(
                    keras.layers.Dense(
                        units,
                        activation=config.activation,
                        kernel_regularizer=keras.regularizers.l2(config.l2_regularization),
                    )
                )
                if config.use_batch_norm:
                    layers.append(keras.layers.BatchNormalization())
                layers.append(keras.layers.Dropout(config.dropout_rate))

            layers.append(
                keras.layers.Dense(
                    config.num_classes,
                    activation=config.output_activation,
                )
            )

            model = keras.Sequential(layers, name=config.name)

        elif config.model_type == ModelType.REGRESSOR:
            layers = [keras.layers.Input(shape=config.input_shape)]

            for units in config.hidden_units:
                layers.append(keras.layers.Dense(units, activation=config.activation))
                layers.append(keras.layers.Dropout(config.dropout_rate))

            layers.append(keras.layers.Dense(config.output_shape[0] if config.output_shape else 1))

            model = keras.Sequential(layers, name=config.name)

        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")

        self._models[config.name] = model
        return model

    def compile(
        self,
        model: Any,
        config: Optional[TrainingConfig] = None,
    ) -> None:
        """
        Compile a model for training.

        Args:
            model: Keras model
            config: Training configuration
        """
        keras = self._get_keras()
        config = config or TrainingConfig()

        optimizer_map = {
            "adam": keras.optimizers.Adam(learning_rate=config.learning_rate),
            "sgd": keras.optimizers.SGD(learning_rate=config.learning_rate),
            "rmsprop": keras.optimizers.RMSprop(learning_rate=config.learning_rate),
        }

        optimizer = optimizer_map.get(
            config.optimizer.lower(),
            keras.optimizers.Adam(learning_rate=config.learning_rate),
        )

        model.compile(
            optimizer=optimizer,
            loss=config.loss,
            metrics=config.metrics,
        )

    def train(
        self,
        model: Any,
        train_data: Tuple[Any, Any],
        config: Optional[TrainingConfig] = None,
        validation_data: Optional[Tuple[Any, Any]] = None,
    ) -> Dict[str, List[float]]:
        """
        Train a model.

        Args:
            model: Keras model
            train_data: Tuple of (X_train, y_train)
            config: Training configuration
            validation_data: Optional validation data

        Returns:
            Training history
        """
        keras = self._get_keras()
        config = config or TrainingConfig()

        callbacks = []

        # Early stopping
        callbacks.append(
            keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=config.early_stopping_patience,
                restore_best_weights=True,
            )
        )

        # Learning rate reduction
        callbacks.append(
            keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=config.reduce_lr_patience,
                min_lr=1e-6,
            )
        )

        # Model checkpoint
        if config.checkpoint_path:
            callbacks.append(
                keras.callbacks.ModelCheckpoint(
                    config.checkpoint_path,
                    monitor="val_loss",
                    save_best_only=True,
                )
            )

        # TensorBoard
        if config.tensorboard_log_dir:
            callbacks.append(
                keras.callbacks.TensorBoard(
                    log_dir=config.tensorboard_log_dir,
                )
            )

        X_train, y_train = train_data

        history = model.fit(
            X_train,
            y_train,
            epochs=config.epochs,
            batch_size=config.batch_size,
            validation_split=config.validation_split if validation_data is None else 0,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=1,
        )

        return history.history

    def predict(
        self,
        model: Any,
        inputs: Any,
        batch_size: int = 32,
    ) -> Any:
        """
        Make predictions with a model.

        Args:
            model: Keras model
            inputs: Input data
            batch_size: Batch size for prediction

        Returns:
            Model predictions
        """
        return model.predict(inputs, batch_size=batch_size)

    async def predict_async(
        self,
        model: Any,
        inputs: Any,
        batch_size: int = 32,
    ) -> Any:
        """
        Make predictions asynchronously.

        Args:
            model: Keras model
            inputs: Input data
            batch_size: Batch size for prediction

        Returns:
            Model predictions
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: model.predict(inputs, batch_size=batch_size),
        )

    def save_model(
        self,
        model: Any,
        name: Optional[str] = None,
    ) -> str:
        """
        Save a model to disk.

        Args:
            model: Keras model
            name: Optional name (uses model name if not provided)

        Returns:
            Path to saved model
        """
        name = name or model.name
        path = self.models_dir / f"{name}.keras"
        model.save(path)
        logger.info(f"Model saved to {path}")
        return str(path)

    def load_model(
        self,
        name: str,
    ) -> Any:
        """
        Load a model from disk.

        Args:
            name: Model name

        Returns:
            Loaded Keras model
        """
        keras = self._get_keras()
        path = self.models_dir / f"{name}.keras"

        if not path.exists():
            # Try .h5 extension
            path = self.models_dir / f"{name}.h5"

        model = keras.models.load_model(path)
        self._models[name] = model
        logger.info(f"Model loaded from {path}")
        return model

    def get_model(self, name: str) -> Optional[Any]:
        """Get a model by name."""
        return self._models.get(name)

    def list_models(self) -> List[str]:
        """List all loaded models."""
        return list(self._models.keys())

    def evaluate(
        self,
        model: Any,
        test_data: Tuple[Any, Any],
        batch_size: int = 32,
    ) -> Dict[str, float]:
        """
        Evaluate a model on test data.

        Args:
            model: Keras model
            test_data: Tuple of (X_test, y_test)
            batch_size: Batch size

        Returns:
            Evaluation metrics
        """
        X_test, y_test = test_data
        results = model.evaluate(X_test, y_test, batch_size=batch_size, return_dict=True)
        return results

    def get_embeddings(
        self,
        model: Any,
        texts: List[str],
        tokenizer: Any,
        max_length: int = 256,
    ) -> Any:
        """
        Get embeddings for texts using an embedding model.

        Args:
            model: Embedding model
            texts: List of texts
            tokenizer: Tokenizer to use
            max_length: Maximum sequence length

        Returns:
            Embedding vectors
        """
        keras = self._get_keras()

        # Tokenize texts
        sequences = tokenizer.texts_to_sequences(texts)
        padded = keras.preprocessing.sequence.pad_sequences(
            sequences,
            maxlen=max_length,
            padding="post",
            truncating="post",
        )

        # Get embeddings
        embeddings = model.predict(padded)
        return embeddings

    def create_tokenizer(
        self,
        texts: List[str],
        vocab_size: int = 10000,
        oov_token: str = "<OOV>",
    ) -> Any:
        """
        Create and fit a tokenizer on texts.

        Args:
            texts: List of texts to fit on
            vocab_size: Maximum vocabulary size
            oov_token: Out-of-vocabulary token

        Returns:
            Fitted tokenizer
        """
        keras = self._get_keras()

        tokenizer = keras.preprocessing.text.Tokenizer(
            num_words=vocab_size,
            oov_token=oov_token,
        )
        tokenizer.fit_on_texts(texts)
        return tokenizer

    def save_tokenizer(self, tokenizer: Any, name: str) -> str:
        """Save a tokenizer to disk."""
        path = self.models_dir / f"{name}_tokenizer.json"
        tokenizer_json = tokenizer.to_json()
        with open(path, "w") as f:
            f.write(tokenizer_json)
        return str(path)

    def load_tokenizer(self, name: str) -> Any:
        """Load a tokenizer from disk."""
        keras = self._get_keras()
        path = self.models_dir / f"{name}_tokenizer.json"
        with open(path, "r") as f:
            tokenizer_json = f.read()
        return keras.preprocessing.text.tokenizer_from_json(tokenizer_json)
