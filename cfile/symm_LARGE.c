
#pragma ACCEL kernel

void kernel_symm(float alpha,float beta,float temp2[1000][1200],float C[1000][1200],float A[1000][1000],float B[1000][1200])
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
    
    
    
    for (i = 0; i < 1000; i++) {
      
      
      
      for (j = 0; j < 1200; j++) {
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
