import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv
import joblib
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class GATClassifier(nn.Module):
    """
    GAT Feature Extractor.
    Input: [N, 396] -> [N, 16] embeddings.
    """

    def __init__(
        self, in_channels: int = 396, embedding_dim: int = 16, num_classes: int = 4
    ):
        super().__init__()
        # Layer 1: Multi-head attention (4 heads, 32 output dim per head)
        self.conv1 = GATv2Conv(in_channels, 32, heads=4, dropout=0.1, edge_dim=1)

        # Layer 2: Final embedding layer (1 head, 16 output dim)
        self.conv2 = GATv2Conv(
            32 * 4, embedding_dim, heads=1, concat=False, dropout=0.1, edge_dim=1
        )

        # Classification head (kept for state_dict compatibility but not used in inference)
        self.classifier = nn.Linear(embedding_dim, num_classes)

    def forward(self, x, edge_index, edge_attr):
        """
        Forward pass returns 16-dim embedding and attention weights from both layers.
        """
        x, (idx1, w1) = self.conv1(
            x, edge_index, edge_attr=edge_attr, return_attention_weights=True
        )
        x = F.elu(x)
        x = F.dropout(x, p=0.1, training=self.training)

        x, (idx2, w2) = self.conv2(
            x, edge_index, edge_attr=edge_attr, return_attention_weights=True
        )
        return x, (idx1, w1), (idx2, w2)


def load_models(data_dir: str = "data"):
    """
    Load all 5 components required for Hybrid AI Inference.
    """
    models = {}

    # 1. Feature Scaler (Numeric Stats)
    scaler_path = os.path.join(data_dir, "scaler.bin")
    if os.path.exists(scaler_path):
        models["feature_scaler"] = joblib.load(scaler_path)
        logger.info(f"Loaded feature_scaler from {scaler_path}")
    else:
        logger.warning(f"Feature scaler not found at {scaler_path}")
        models["feature_scaler"] = None

    # 2. NLP Model (SentenceTransformer)
    try:
        models["nlp_model"] = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        logger.info("Loaded nlp_model (all-MiniLM-L6-v2)")
    except Exception as e:
        logger.error(f"Failed to load nlp_model: {e}")
        models["nlp_model"] = None

    # 3. GAT Model (Feature Extractor)
    gat_path = os.path.join(data_dir, "best_gat_model.pth")
    gat_model = GATClassifier(in_channels=396, embedding_dim=16, num_classes=4)
    if os.path.exists(gat_path):
        try:
            # map_location='cpu' for safe loading on different devices
            state_dict = torch.load(gat_path, map_location="cpu", weights_only=False)
            gat_model.load_state_dict(state_dict)
            gat_model.eval()
            models["gat_model"] = gat_model
            logger.info(f"Loaded gat_model from {gat_path}")
        except Exception as e:
            logger.error(f"Failed to load gat_model state_dict: {e}")
            models["gat_model"] = gat_model
    else:
        logger.warning(f"GAT model not found at {gat_path}")
        models["gat_model"] = gat_model

    # 4. Embedding Scaler (for GAT output)
    emb_scaler_path = os.path.join(data_dir, "scaler_gat_ml.pkl")
    if os.path.exists(emb_scaler_path):
        models["embedding_scaler"] = joblib.load(emb_scaler_path)
        logger.info(f"Loaded embedding_scaler from {emb_scaler_path}")
    else:
        logger.warning(f"Embedding scaler not found at {emb_scaler_path}")
        models["embedding_scaler"] = None

    # 5. Random Forest Model (Final Classifier)
    rf_path = os.path.join(data_dir, "random_forest_gat.pkl")
    if os.path.exists(rf_path):
        models["rf_model"] = joblib.load(rf_path)
        logger.info(f"Loaded rf_model from {rf_path}")
    else:
        logger.warning(f"RF model not found at {rf_path}")
        models["rf_model"] = None

    return models
