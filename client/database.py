import sqlite3
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

def load_data(school_name, db_dir="data/partitions", batch_size=32, test_split=0.2):
    db_path = f"{db_dir}/{school_name}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            attendance_rate,
            quiz_score,
            assignment_submission_rate,
            login_frequency,
            days_since_last_activity,
            course_difficulty,
            prior_score,
            engagement_index,
            at_risk
        FROM students
    """)
    records = cursor.fetchall()
    conn.close()
    
    data = np.array(records, dtype=np.float32)
    X = data[:, :-1]
    y = data[:, -1:]
    
    # Normalize features locally
    # 1. attendance_rate: 0.0 - 1.0 (already standard)
    # 2. quiz_score: 0 - 100 -> normalize by /100.0
    X[:, 1] = X[:, 1] / 100.0
    # 3. assignment_submission_rate: 0.0 - 1.0
    # 4. login_frequency: 0 - 30 -> normalize by /30.0
    X[:, 3] = X[:, 3] / 30.0
    # 5. days_since_last_activity: 0 - 60 -> normalize by /60.0
    X[:, 4] = X[:, 4] / 60.0
    # 6. course_difficulty: 1 - 5 -> normalize by /5.0
    X[:, 5] = X[:, 5] / 5.0
    # 7. prior_score: 0 - 100 -> normalize by /100.0
    X[:, 6] = X[:, 6] / 100.0
    # 8. engagement_index: 0 - 100 -> normalize by /100.0
    X[:, 7] = X[:, 7] / 100.0

    # Shuffle and Split into train/test
    num_samples = len(X)
    indices = np.arange(num_samples)
    np.random.seed(42)
    np.random.shuffle(indices)
    
    X = X[indices]
    y = y[indices]
    
    split_idx = int(num_samples * (1.0 - test_split))
    
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    test_ds = TensorDataset(torch.tensor(X_test), torch.tensor(y_test))
    
    # Use drop_last=True for Opacus if batch sizes are strict, but standard is fine
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader, len(X_train), len(X_test)
