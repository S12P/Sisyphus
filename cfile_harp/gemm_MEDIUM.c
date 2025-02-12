
#pragma ACCEL kernel

void kernel_gemm(double alpha,double beta,double C[200][220],double A[200][240],double B[240][220])
{
  int i;
  int j;
  int k;

{
    
    
    
    for (i = 0; i < 200; i++) {
      
      for (j = 0; j < 220; j++) {
        C[i][j] *= beta;
      }
      
      
      for (j = 0; j < 220; j++) {
        for (k = 0; k < 240; k++) {
        
        
          C[i][j] += alpha * A[i][k] * B[k][j];
        }
      }
    }
  }
}
