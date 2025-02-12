
#pragma ACCEL kernel

void kernel_trisolv(float L[400][400],float x[400],float b[400])
{
  int i;
  int j;
{
    
    
    
    for (i = 0; i < 400; i++) {
      x[i] = b[i];
      for (j = 0; j < i; j++) {
        x[i] -= L[i][j] * x[j];
      }
      x[i] = x[i] / L[i][i];
    }
  }
}
