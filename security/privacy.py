from opacus import PrivacyEngine
import warnings

def make_private_training(model, optimizer, train_loader, noise_multiplier=1.1, max_grad_norm=1.0):
    """
    Wrap PyTorch model, optimizer, and data_loader for DP-SGD training using Opacus.
    """
    # Suppress Opacus warnings about non-standard modules if any
    warnings.filterwarnings("ignore", category=UserWarning, module="opacus")
    
    privacy_engine = PrivacyEngine()
    model, optimizer, train_loader = privacy_engine.make_private(
        module=model,
        optimizer=optimizer,
        data_loader=train_loader,
        noise_multiplier=noise_multiplier,
        max_grad_norm=max_grad_norm,
    )
    return model, optimizer, train_loader, privacy_engine

def get_privacy_spent(privacy_engine, delta=1e-5):
    """Get the current epsilon value from the privacy engine."""
    if privacy_engine is None:
        return 0.0
    try:
        return privacy_engine.get_epsilon(delta)
    except Exception:
        return 0.0
