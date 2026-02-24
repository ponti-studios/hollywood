import numpy as np
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BudgetLSTM(nn.Module):
    def __init__(self, input_size=1, hidden_size=32, num_layers=2, output_size=1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        batch_size = x.size(0)
        h0 = torch.zeros(self.num_layers, batch_size, self.hidden_size)
        c0 = torch.zeros(self.num_layers, batch_size, self.hidden_size)

        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


def prepare_data(data, sequence_length):
    """Prepare sequences for LSTM training"""
    start_time = time.time()
    logger.info("Starting data preparation...")

    sequences = []
    targets = []

    for i in range(len(data) - sequence_length):
        sequences.append(data[i : i + sequence_length])
        targets.append(data[i + sequence_length])

    sequences = np.array(sequences)
    targets = np.array(targets)

    logger.info(f"Data preparation completed in {time.time() - start_time:.2f} seconds")
    return torch.FloatTensor(sequences), torch.FloatTensor(targets)


def train_model(model, train_data, sequence_length, epochs=100, lr=0.01):
    """Train the LSTM model"""
    start_time = time.time()
    logger.info("Starting model training...")

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    X, y = prepare_data(train_data, sequence_length)
    X = X.unsqueeze(-1)  # Add feature dimension
    y = y.unsqueeze(-1)  # Adjust target shape to match output

    for epoch in range(epochs):
        epoch_start = time.time()
        model.train()
        optimizer.zero_grad()

        outputs = model(X)
        loss = criterion(outputs, y)

        loss.backward()
        optimizer.step()

        if (epoch + 1) % 20 == 0:
            epoch_time = time.time() - epoch_start
            logger.info(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}, Time: {epoch_time:.2f}s")

    total_time = time.time() - start_time
    logger.info(f"Model training completed in {total_time:.2f} seconds")


def forecast_budget(model, last_sequence, num_predictions):
    """Generate future budget predictions"""
    start_time = time.time()
    logger.info("Starting budget forecasting...")

    model.eval()
    predictions = []
    current_sequence = last_sequence.copy()

    for _ in range(num_predictions):
        with torch.no_grad():
            x = torch.FloatTensor(current_sequence).unsqueeze(0).unsqueeze(-1)
            prediction = model(x)
            predictions.append(prediction.item())
            current_sequence = np.append(current_sequence[1:], prediction.item())

    logger.info(f"Forecasting completed in {time.time() - start_time:.2f} seconds")
    return predictions


# Example usage
if __name__ == "__main__":
    total_start_time = time.time()
    logger.info("Starting budget forecasting application...")

    # Sample monthly budget data (revenue)
    budget_data = np.array(
        [
            5000,
            5200,
            4800,
            6000,
            5500,
            5800,
            6200,
            6500,
            6300,
            7000,
            6800,
            7200,
            7500,
            7300,
            7800,
            8000,
            7900,
            8200,
        ]
    )

    logger.info("Normalizing data...")
    # Normalize data
    scaler = MinMaxScaler()
    normalized_data = scaler.fit_transform(np.array(budget_data).reshape(-1, 1)).flatten()

    # Model parameters
    sequence_length = 6  # Use 6 months to predict next month

    # Initialize and train model
    model = BudgetLSTM()
    train_model(model, normalized_data, sequence_length)

    # Prepare last sequence for forecasting
    last_sequence = normalized_data[-sequence_length:]

    logger.info("Generating forecast...")
    # Generate 6-month forecast
    predictions = forecast_budget(model, last_sequence, 6)

    logger.info("Denormalizing predictions...")
    # Denormalize predictions
    denormalized_predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten()

    print("\nBudget Forecast for Next 6 Months:")
    for i, pred in enumerate(denormalized_predictions, 1):
        print(f"Month {i}: ${pred:.2f}")

    total_time = time.time() - total_start_time
    logger.info(f"Total execution time: {total_time:.2f} seconds")
