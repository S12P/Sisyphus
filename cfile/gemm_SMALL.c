
#pragma ACCEL kernel

void kernel_gemm(float alpha,float beta,float C[60][70],float A[60][80],float B[80][70])
{
  int i;
  int j;
  int k;
//BLAS PARAMS
//TRANSA = 'N'
//TRANSB = 'N'
// => Form C := alpha*A*B + beta*C,
//A is NIxNK
//B is NKxNJ
//C is NIxNJ
{
    
    
    
    for (i = 0; i < 60; i++) {
      
      for (j = 0; j < 70; j++) {
        C[i][j] *= beta;
      }
      
      
      for (j = 0; j < 70; j++) {
        for (k = 0; k < 80; k++) {
        
        
          C[i][j] += alpha * A[i][k] * B[k][j];
        }
      }
    }
  }
}
