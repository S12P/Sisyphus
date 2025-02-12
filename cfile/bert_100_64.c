


void kernel_gemm(float C[100][64],float A[100][100],float B[100][64])
{
    int i;
    int j;
    int k;
    
    for (i = 0; i < 100; i++) {
        
        for (j = 0; j < 64; j++) {
            C[i][j] = 0;
            for (k = 0; k < 100; k++) {
                C[i][j] +=  A[i][k] * B[k][j];
            }
        }
    }
}

