import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Mock data
# 394 points
data = np.random.rand(394) * 100
df_train = pd.DataFrame({'CANTIDAD': data})

periodos_prediccion = 5

print(f"Data length: {len(df_train)}")
print(f"Prediction steps: {periodos_prediccion}")

try:
    model = SARIMAX(df_train['CANTIDAD'], order=(1,1,1), seasonal_order=(1,1,1,52))
    results = model.fit(disp=False)
    
    forecast = results.forecast(steps=periodos_prediccion)
    print("Forecast successful:")
    print(forecast)
except Exception as e:
    print(f"SARIMA failed: {e}")
    import traceback
    traceback.print_exc()
