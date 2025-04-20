import { FC } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Paper, 
  Button,
  Grid,
  CircularProgress,
  IconButton
} from '@mui/material';
import FileUploader from './FileUploader';

interface LandingPageProps {
  file: File | null;
  isProcessing: boolean;
  onFileUpload: (content: string) => void;
  onProcessDataset: () => void;
  onRemoveFile?: () => void;
}

const LandingPage: FC<LandingPageProps> = ({
  file,
  isProcessing,
  onFileUpload,
  onProcessDataset,
  onRemoveFile
}) => {
  return (
    <>
      <Box 
        sx={{ 
          py: 6,
          mb: 5,
          background: 'linear-gradient(to bottom, rgba(25, 118, 210, 0.15), rgba(0, 0, 0, 0))',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ textAlign: 'center', mb: 5 }}>
            <Typography 
              variant="h2" 
              gutterBottom 
              sx={{ 
                fontWeight: 700, 
                mb: 1,
                background: 'linear-gradient(90deg, #90caf9 0%, #ce93d8 100%)',
                backgroundClip: 'text',
                textFillColor: 'transparent',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              PL1 Learning System
            </Typography>
            <Typography 
              variant="h5" 
              color="text.secondary" 
              sx={{ 
                mb: 4, 
                maxWidth: '800px',
                mx: 'auto',
                lineHeight: 1.5
              }}
            >
              Inovatívny systém pre učenie konceptov pomocou symbolickej notácie predikátovej logiky prvého rádu
            </Typography>
          </Box>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ mb: 6 }}>
        <Grid container spacing={5}>
          <Grid item xs={12} md={6} id="upload-section">
            <Paper 
              elevation={6} 
              sx={{ 
                height: '100%', 
                p: { xs: 3, sm: 4, md: 4.5 },
                borderRadius: 4,
                background: 'linear-gradient(145deg, rgba(30,30,30,1) 0%, rgba(40,40,40,1) 100%)',
                boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <Box 
                sx={{ 
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 6,
                  background: 'linear-gradient(90deg, #90caf9 0%, #ce93d8 100%)',
                }}
              />

              <Typography 
                variant="h4" 
                gutterBottom
                sx={{ 
                  fontWeight: 600, 
                  mb: 1,
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                <Box 
                  sx={{ 
                    display: 'inline-flex', 
                    p: 1, 
                    borderRadius: '50%', 
                    background: 'rgba(144, 202, 249, 0.1)',
                    mr: 1
                  }}
                >
                  <span style={{ fontSize: '1.4rem' }}>📊</span>
                </Box>
                Nahrať dataset
              </Typography>

              <Typography 
                variant="body1" 
                paragraph
                sx={{ 
                  mb: 3.5,
                  color: 'rgba(255,255,255,0.7)',
                  lineHeight: 1.7,
                  fontSize: '1.05rem'
                }}
              >
                Nahrajte súbor s datasetom vo formáte PL1 pre trénovanie modelu. Váš dataset by mal 
                obsahovať pozitívne a negatívne príklady zapísané v symbolickej notácii predikátovej logiky.
              </Typography>
              
              <Box
                sx={{
                  border: '2px dashed rgba(144, 202, 249, 0.3)', 
                  borderRadius: 3,
                  p: 3.5,
                  mb: 3.5,
                  transition: 'all 0.2s ease',
                  background: file ? 'rgba(102, 187, 106, 0.1)' : 'rgba(144, 202, 249, 0.05)',
                  borderColor: file ? 'rgba(102, 187, 106, 0.4)' : 'rgba(144, 202, 249, 0.3)',
                  '&:hover': {
                    borderColor: file ? 'rgba(102, 187, 106, 0.6)' : 'rgba(144, 202, 249, 0.5)',
                    background: file ? 'rgba(102, 187, 106, 0.15)' : 'rgba(144, 202, 249, 0.08)',
                  }
                }}
              >
                <FileUploader onFileUpload={onFileUpload} />
                
                {file && (
                  <Box sx={{ 
                    mt: 2, 
                    p: 1.5, 
                    borderRadius: 2, 
                    bgcolor: 'rgba(102, 187, 106, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box sx={{ 
                        mr: 1.5, 
                        color: 'success.main', 
                        display: 'flex', 
                        alignItems: 'center' 
                      }}>
                        <span style={{ fontSize: '1.2rem' }}>✓</span>
                      </Box>
                      <Typography variant="body2" sx={{ fontWeight: 500, color: 'rgba(255,255,255,0.9)' }}>
                        {file.name.replace('uploaded-file.txt', 'dataset.txt')} ({(file.size / 1024).toFixed(1)} KB)
                      </Typography>
                    </Box>
                    <IconButton 
                      size="small" 
                      onClick={onRemoveFile}
                      sx={{ 
                        color: 'rgba(255,255,255,0.6)', 
                        '&:hover': { 
                          color: 'rgba(255,255,255,0.9)',
                          bgcolor: 'rgba(255,255,255,0.1)'
                        }
                      }}
                    >
                      <span style={{ fontSize: '1rem' }}>✕</span>
                    </IconButton>
                  </Box>
                )}
              </Box>
              
              <Button
                variant="contained"
                color="primary"
                fullWidth
                size="large"
                sx={{ 
                  mt: 2,
                  py: 1.5,
                  borderRadius: 2,
                  fontSize: '1.05rem',
                  boxShadow: '0 4px 12px rgba(25, 118, 210, 0.4)',
                  position: 'relative',
                  overflow: 'hidden',
                  '&:hover': {
                    boxShadow: '0 6px 16px rgba(25, 118, 210, 0.6)',
                  },
                  '&:after': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: '-100%',
                    width: '100%',
                    height: '100%',
                    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
                    transition: 'all 0.5s ease',
                  },
                  '&:hover:after': {
                    left: '100%',
                  }
                }}
                disabled={!file || isProcessing}
                onClick={onProcessDataset}
              >
                {isProcessing ? (
                  <>
                    <CircularProgress size={24} color="inherit" sx={{ mr: 2 }} />
                    Spracovávam dataset...
                  </>
                ) : (
                  'Spracovať dataset'
                )}
              </Button>

              <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
                <Typography variant="caption" color="text.secondary" align="center">
                  Podporované formáty: .txt alebo .pl1 s PL1 formulami
                </Typography>
              </Box>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={6} id="about-section">
            <Paper 
              elevation={6} 
              sx={{ 
                height: '100%', 
                p: { xs: 3, sm: 4, md: 5 },
                borderRadius: 4,
                background: 'linear-gradient(145deg, rgba(30,30,30,1) 0%, rgba(40,40,40,1) 100%)',
                boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <Box 
                sx={{ 
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 6,
                  background: 'linear-gradient(90deg, #ce93d8 0%, #66bb6a 100%)',
                }}
              />

              <Typography 
                variant="h4" 
                gutterBottom
                sx={{ 
                  fontWeight: 600, 
                  mb: 2, 
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                <Box 
                  sx={{ 
                    display: 'inline-flex', 
                    p: 1, 
                    borderRadius: '50%', 
                    background: 'rgba(206, 147, 216, 0.1)',
                    mr: 1
                  }}
                >
                  <span style={{ fontSize: '1.4rem' }}>🧠</span>
                </Box>
                O projekte
              </Typography>

              <Typography 
                sx={{ 
                  mb: 2,
                  color: 'rgba(255,255,255,0.7)',
                  lineHeight: 1.6,
                  fontSize: '1rem'
                }}
              >
                Tento projekt implementuje pokročilý systém pre učenie konceptov pomocou 
                pozitívnych a negatívnych príkladov. Systém využíva heuristiky Winstonovho algoritmu učenia 
                konceptov a reprezentuje znalosti pomocou symbolickej notácie predikátovej logiky prvého rádu.
              </Typography>

              <Typography 
                variant="h6" 
                sx={{ 
                  mb: 2,
                  mt: 3.5,
                  color: '#fff',
                  fontWeight: 600,
                }}
              >
                Kľúčové funkcie
              </Typography>

              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6}>
                  <Box 
                    sx={{ 
                      p: 2,
                      borderRadius: 2,
                      background: 'rgba(144, 202, 249, 0.08)',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Box 
                        sx={{ 
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 32,
                          height: 32,
                          borderRadius: '50%',
                          background: 'rgba(144, 202, 249, 0.15)',
                          mr: 1.5
                        }}
                      >
                        <span style={{ fontSize: '1rem' }}>📝</span>
                      </Box>
                      <Typography 
                        variant="subtitle1" 
                        sx={{ 
                          fontWeight: 600, 
                          color: 'primary.light'
                        }}
                      >
                        Symbolické spracovanie
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                      Parsovanie a spracovanie príkladov v notácii PL1
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box 
                    sx={{ 
                      p: 2,
                      borderRadius: 2,
                      background: 'rgba(206, 147, 216, 0.08)',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Box 
                        sx={{ 
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 32,
                          height: 32,
                          borderRadius: '50%',
                          background: 'rgba(206, 147, 216, 0.15)',
                          mr: 1.5
                        }}
                      >
                        <span style={{ fontSize: '1rem' }}>🔄</span>
                      </Box>
                      <Typography 
                        variant="subtitle1" 
                        sx={{ 
                          fontWeight: 600, 
                          color: 'secondary.light'
                        }}
                      >
                        Winstonove heuristiky
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                      Učenie konceptov pomocou efektívnych heuristík
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box 
                    sx={{ 
                      p: 2,
                      borderRadius: 2,
                      background: 'rgba(102, 187, 106, 0.08)',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Box 
                        sx={{ 
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 32,
                          height: 32,
                          borderRadius: '50%',
                          background: 'rgba(102, 187, 106, 0.15)',
                          mr: 1.5
                        }}
                      >
                        <span style={{ fontSize: '1rem' }}>🔍</span>
                      </Box>
                      <Typography 
                        variant="subtitle1" 
                        sx={{ 
                          fontWeight: 600, 
                          color: 'success.light'
                        }}
                      >
                        Porovnávanie príkladov
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                      Porovnávanie nových príkladov s naučeným modelom
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box 
                    sx={{ 
                      p: 2,
                      borderRadius: 2,
                      background: 'rgba(244, 67, 54, 0.08)',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Box 
                        sx={{ 
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 32,
                          height: 32,
                          borderRadius: '50%',
                          background: 'rgba(244, 67, 54, 0.15)',
                          mr: 1.5
                        }}
                      >
                        <span style={{ fontSize: '1rem' }}>📊</span>
                      </Box>
                      <Typography 
                        variant="subtitle1" 
                        sx={{ 
                          fontWeight: 600, 
                          color: 'error.light'
                        }}
                      >
                        Vizualizácia siete
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                      Vizualizácia modelu ako sémantickej siete
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              <Box 
                sx={{ 
                  mt: 4,
                  pt: 3,
                  borderTop: '1px solid rgba(255,255,255,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: 2
                }}
              >
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                  © 2025 PL1 Learning System
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </>
  );
};

export default LandingPage; 