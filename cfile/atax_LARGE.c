
#pragma ACCEL kernel

void kernel_atax(float A[1900][2100],float x[2100],float y[2100],float tmp[1900])
{
  int i;
  int j;
{
    
    for (i = 0; i < 2100; i++) {
      y[i] = 0.0;
    }
    
    
    
    for (i = 0; i < 1900; i++) {
      tmp[i] = 0.0;
    }
      
    for (i = 0; i < 1900; i++) {
      for (j = 0; j < 2100; j++) {
        tmp[i] = tmp[i] + A[i][j] * x[j];
      }
    }
    for (j = 0; j < 2100; j++) {
      for (i = 0; i < 1900; i++) {  
      
        y[j] = y[j] + A[i][j] * tmp[i];
      }
    }
  }
}
