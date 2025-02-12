
#pragma ACCEL kernel

void kernel_symm(float alpha,float beta,float temp2[200][240], float C[200][240],float A[200][200],float B[200][240])
{
  
  int i;
  int j;
  int k;
  
//BLAS PARAMS
//SIDE = 'L'
//UPLO = 'L'
// =>  Form  C := alpha*A*B + beta*C
// A is MxM
// B is MxN
// C is MxN
//note that due to Fortran array layout, the code below more closely resembles upper triangular case in BLAS
{
    
    
    
    for (i = 0; i < 200; i++) {
      for (j = 0; j < 240; j++) {
        temp2[i][j] = 0;
      }
    }
    for (i = 0; i < 200; i++) {
      for (j = 0; j < 240; j++) {
        for (k = 0; k < i; k++) {
          temp2[i][j] += B[k][j] * A[i][k];
        }
      }
    }
    for (i = 0; i < 200; i++) {
      for (j = 0; j < 240; j++) {
        C[i][j] = beta * C[i][j] + alpha * B[i][j] * A[i][i] + alpha * temp2[i][j];
      }
    }
    for (i = 0; i < 200; i++) {
      for (j = 0; j < 240; j++) {
        for (k = 0; k < i; k++) {
          C[k][j] += alpha * B[i][j] * A[i][k];
        }
      }
    }
  }
}
