
#pragma ACCEL kernel

void kernel_gemver(double alpha,double beta,double A[400][400],double u1[400],double e1[400],double u2[400],double e2[400],double w[400],double x[400],double y[400],double z[400])
{
  int i;
  int j;
{
    
    
    
    for (i = 0; i < 400; i++) {
      
      for (j = 0; j < 400; j++) {
        A[i][j] = A[i][j] + u1[i] * e1[j] + u2[i] * e2[j];
      }
    }
    
    
    
    for (i = 0; i < 400; i++) {
      
      for (j = 0; j < 400; j++) {
        x[i] = x[i] + beta * A[j][i] * y[j];
      }
    }
    
    for (i = 0; i < 400; i++) {
      x[i] = x[i] + z[i];
    }
    
    
    
    for (i = 0; i < 400; i++) {
      
      for (j = 0; j < 400; j++) {
        w[i] = w[i] + alpha * A[i][j] * x[j];
      }
    }
  }
}
