
#pragma ACCEL kernel

void kernel_trisolv(float L[120][120],float x[120],float b[120])
{
  int i;
  int j;
{
    
    
    
    for (i = 0; i < 120; i++) {
      x[i] = b[i];
      for (j = 0; j < i; j++) {
        x[i] -= L[i][j] * x[j];
      }
      x[i] = x[i] / L[i][i];
    }
  }
}
