


void kernel_gemm(float C[3072][100],float A[3072][3072],float B[3072][100])
{
    int i;
    int j;
    int k;
    
    for (i = 0; i < 3072; i++) {
        
        for (j = 0; j < 100; j++) {
            C[i][j] = 0;
            for (k = 0; k < 3072; k++) {
                C[i][j] +=  A[i][k] * B[k][j];
            }
        }
    }
}

