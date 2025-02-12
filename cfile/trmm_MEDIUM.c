
#pragma ACCEL kernel

void kernel_trmm(float alpha,float A[200][200],float B[200][240], float B2[200][240])
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
    
    
    
    for (i = 0; i < 200; i++) {
      
      
      
      for (j = 0; j < 240; j++) {
        for (k = i + 1; k < 200; k++) {
          B[i][j] += A[k][i] * B2[k][j];
        }
        B[i][j] = alpha * B[i][j];
      }
    }
  }
}
