
#pragma ACCEL kernel

void kernel_atax(float A[116][124],float x[124],float y[124],float tmp[116])
{
  int i;
  int j;
{
    
    for (i = 0; i < 124; i++) {
      y[i] = 0.0;
    }
    
    
    
    for (i = 0; i < 116; i++) {
      tmp[i] = 0.0;
      
      for (j = 0; j < 124; j++) {
        tmp[i] = tmp[i] + A[i][j] * x[j];
      }
      
      for (j = 0; j < 124; j++) {
        y[j] = y[j] + A[i][j] * tmp[i];
      }
    }
  }
}
