
#pragma ACCEL kernel

void kernel_gesummv(float alpha,float beta,float A[90][90],float B[90][90],float tmp[90],float x[90],float y[90])
{
  int i;
  int j;
{
    
    
    
    for (i = 0; i < 90; i++) {
      tmp[i] = 0.0;
      y[i] = 0.0;
      
      for (j = 0; j < 90; j++) {
        tmp[i] = A[i][j] * x[j] + tmp[i];
        y[i] = B[i][j] * x[j] + y[i];
      }
      y[i] = alpha * tmp[i] + beta * y[i];
    }
  }
}
