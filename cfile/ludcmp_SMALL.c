
#pragma ACCEL kernel

void kernel_ludcmp(float A[120][120],float b[120],float x[120],float y[120])
{
  int i;
  int j;
  int k;
  float w;
{
    
    
    
    for (i = 0; i < 120; i++) {
      
      for (j = 0; j < i; j++) {
        w = A[i][j];
        for (k = 0; k < j; k++) {
          w -= A[i][k] * A[k][j];
        }
        A[i][j] = w / A[j][j];
      }
      
      for (j = i; j < 120; j++) {
        w = A[i][j];
        for (k = 0; k < i; k++) {
          w -= A[i][k] * A[k][j];
        }
        A[i][j] = w;
      }
    }
    
    
    
    for (i = 0; i < 120; i++) {
      w = b[i];
      for (j = 0; j < i; j++) {
        w -= A[i][j] * y[j];
      }
      y[i] = w;
    }
    
    
    
    for (i = 0; i <= 119; i++) {
      w = y[119 + -1 * i];
      for (j = 119 + -1 * i + 1; j < 120; j++) {
        w -= A[119 + -1 * i][j] * x[j];
      }
      x[119 + -1 * i] = w / A[119 + -1 * i][119 + -1 * i];
    }
  }
}
