
#pragma ACCEL kernel

void kernel_trisolv(float L[2000][2000],float x[2000],float b[2000])
{
  int i;
  int j;
{
    
    
    
    for (i = 0; i < 2000; i++) {
      x[i] = b[i];
      for (j = 0; j < i; j++) {
        x[i] -= L[i][j] * x[j];
      }
      x[i] = x[i] / L[i][i];
    }
  }
}
