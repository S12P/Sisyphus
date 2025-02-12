
#pragma ACCEL kernel

void kernel_trmm(float alpha,float A[1000][1000],float B[1000][1200])
{
  int i;
  int j;
  int k;
//BLAS parameters
//SIDE   = 'L'
//UPLO   = 'L'
//TRANSA = 'T'
//DIAG   = 'U'
// => Form  B := alpha*A**T*B.
// A is MxM
// B is MxN
{
    
    
    
    for (i = 0; i < 1000; i++) {
      
      
      
      for (j = 0; j < 1200; j++) {
        for (k = i + 1; k < 1000; k++) {
          B[i][j] += A[k][i] * B[k][j];
        }
        B[i][j] = alpha * B[i][j];
      }
    }
  }
}
