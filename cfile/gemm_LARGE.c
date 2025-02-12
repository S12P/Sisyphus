
#pragma ACCEL kernel

void kernel_gemm(float alpha,float beta,float C[1000][1100],float A[1000][1200],float B[1200][1100])
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
    
    
    
    for (i = 0; i < 1000; i++) {
      
      for (j = 0; j < 1100; j++) {
        C[i][j] *= beta;
      }
      
      
      for (j = 0; j < 1100; j++) {
        for (k = 0; k < 1200; k++) {
        
        
          C[i][j] += alpha * A[i][k] * B[k][j];
        }
      }
    }
  }
}
