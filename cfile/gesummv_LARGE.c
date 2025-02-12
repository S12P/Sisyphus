
#pragma ACCEL kernel

void kernel_gesummv(float alpha,float beta,float A[1300][1300],float B[1300][1300],float tmp[1300],float x[1300],float y[1300])
{
  int i;
  int j;
{
    
    

    for (i = 0; i < 1300; i++) {
      tmp[i] = 0.0;
      y[i] = 0.0;
      
      for (j = 0; j < 1300; j++) {
        tmp[i] = A[i][j] * x[j] + tmp[i];
        y[i] = B[i][j] * x[j] + y[i];
      }
      y[i] = alpha * tmp[i] + beta * y[i];
    }
  }
}
