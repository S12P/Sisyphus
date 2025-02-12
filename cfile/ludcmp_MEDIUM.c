
#pragma ACCEL kernel

void kernel_ludcmp(float A[400][400],float b[400],float x[400],float y[400])
{
  float w1[400][400];
  int i;
  int j;
  int k;
  
{
    
    
    
    for (i = 0; i < 400; i++) {
      
      for (j = 0; j < i; j++) {
        w1[i][j] = A[i][j];
        for (k = 0; k < j; k++) {
          w1[i][j] -= A[i][k] * A[k][j];
        }
        A[i][j] = w1[i][j] / A[j][j];
      }
      
      for (j = i; j < 400; j++) {
        w1[i][j] = A[i][j];
        for (k = 0; k < i; k++) {
          w1[i][j] -= A[i][k] * A[k][j];
        }
        A[i][j] = w1[i][j];
      }
    }
    
    
    
    for (i = 0; i < 400; i++) {
      w1[0][i] = b[i];
      for (j = 0; j < i; j++) {
        w1[0][i] -= A[i][j] * y[j];
      }
      y[i] = w1[0][i];
    }
    
    
    
    for (i = 0; i <= 399; i++) {
      w1[0][i] = y[399 + -i];
      for (j = 399 + -i + 1; j < 400; j++) {
        w1[0][i] -= A[399 + -i][j] * x[j];
      }
      x[399 + -i] = w1[0][i] / A[399 + -i][399 + -i];
    }
    // i = 0 + -1;
  }
}
