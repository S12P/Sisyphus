
#pragma ACCEL kernel

void kernel_syr2k(float alpha,float beta,float C[240][240],float A[240][200],float B[240][200])
{
  int i;
  int j;
  int k;
//BLAS PARAMS
//UPLO  = 'L'
//TRANS = 'N'
//A is NxM
//B is NxM
//C is NxN
{
    
    
    
    for (i = 0; i < 240; i++) {
      for (j = 0; j <= i; j++) {
        C[i][j] *= beta;
      }
      
      
      
      for (k = 0; k < 200; k++) {
        for (j = 0; j <= i; j++) {
          C[i][j] += A[j][k] * alpha * B[i][k] + B[j][k] * alpha * A[i][k];
        }
      }
    }
  }
}
