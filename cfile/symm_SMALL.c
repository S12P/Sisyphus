
#pragma ACCEL kernel

void kernel_symm(float alpha,float beta,float temp2[60][80],float C[60][80],float A[60][60],float B[60][80])
{
  ;
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
    
    
    
    for (i = 0; i < 60; i++) {
      
      
      
      for (j = 0; j < 80; j++) {
        temp2[i][j] = 0;
        for (k = 0; k < i; k++) {
          C[k][j] += alpha * B[i][j] * A[i][k];
          temp2[i][j] += B[k][j] * A[i][k];
        }
        C[i][j] = beta * C[i][j] + alpha * B[i][j] * A[i][i] + alpha * temp2[i][j];
      }
    }
  }
}
