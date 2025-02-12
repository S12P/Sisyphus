
#pragma ACCEL kernel

void kernel_trmm(float alpha,float A[60][60],float B[60][80])
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
    
    
    
    for (i = 0; i < 60; i++) {
      
      
      
      for (j = 0; j < 80; j++) {
        for (k = i + 1; k < 60; k++) {
          B[i][j] += A[k][i] * B[k][j];
        }
        B[i][j] = alpha * B[i][j];
      }
    }
  }
}
