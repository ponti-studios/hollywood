import torch
import torch.nn as nn
import torch.optim as optim


def convert_to_fahrenheit(celsius) -> float:
    return celsius * 9 / 5 + 32


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(1, 1)

    def forward(self, input):
        out = self.linear(input)
        return out


# Input: x
# Weight: w
# Bias: b
# y = wx + b

model = Model()

# Compare the output to the desired output. This enables prediction accuracy.
mse = nn.MSELoss()

# Stochastic Gradient Descent.
# Setting a lower learning rate enables the model to learn more accurately at the expense of speed.
optimizer = optim.SGD(model.parameters(), lr=0.01)

inputs = torch.rand((5, 1), dtype=torch.float32)

# The model should predict a value close to the expected output (input * factor).
# factor = 2

# The target output is a linear transformation of the input.
targets = convert_to_fahrenheit(inputs)

# Training iterations
for epoch in range(10000):
    # Forward pass
    outputs = model.forward(inputs)

    # Compute the loss between the model output and the target
    loss = mse(outputs, targets)

    # Backward pass and optimization
    optimizer.zero_grad()  # Clear the old gradients before performing the backward pass.
    loss.backward()  # Compute the gradients of the loss with respect to the model parameters.
    optimizer.step()  # Update the model parameters using the gradients.

    # Print the loss every 100 epochs to monitor training progress.
    if epoch % 100 == 0:
        print(f"Epoch {epoch}, Loss: {loss.item()}")


# After training, test the model with a new input
test_input = torch.tensor([[23.0]], dtype=torch.float32)

predicted_output = model.forward(test_input)

print(
    f"Input: {test_input.item()}, Model Prediction: {predicted_output.item()}, Expected: {convert_to_fahrenheit(test_input.item())}"
)
