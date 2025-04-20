import { useCallback } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { useDropzone } from 'react-dropzone';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

interface FileUploaderProps {
  onFileUpload: (content: string, fileName?: string) => void;
}

const FileUploader = ({ onFileUpload }: FileUploaderProps) => {
  const handleDrop = useCallback(
    (acceptedFiles: Array<File>) => {
      const file = acceptedFiles[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = () => {
          const content = reader.result as string;
          onFileUpload(content, file.name);
        };
        reader.readAsText(file);
      }
    },
    [onFileUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop: handleDrop,
    accept: {
      'text/plain': ['.txt', '.pl1']
    },
    maxFiles: 1
  });

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      const reader = new FileReader();
      reader.onload = () => {
        const content = reader.result as string;
        onFileUpload(content, file.name);
      };
      reader.readAsText(file);
    }
  };

  return (
    <Paper
      sx={{
        p: 3,
        mt: 2,
        mb: 3,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        backgroundColor: 'rgba(30, 30, 30, 0.6)',
        borderRadius: 2,
        cursor: 'pointer'
      }}
      {...getRootProps()}
    >
      <input {...getInputProps()} />
      <CloudUploadIcon sx={{ fontSize: 60, mb: 2, color: 'primary.main' }} />
      
      <Box textAlign="center">
        {isDragActive ? (
          <Typography variant="h6">Pustite súbor tu...</Typography>
        ) : (
          <>
            <Typography variant="h6" gutterBottom>
              Presuňte sem súbor s príkladmi alebo kliknite pre výber
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Podporované formáty: .txt alebo .pl1 s PL1 formulami
            </Typography>
          </>
        )}
      </Box>
    </Paper>
  );
};

export default FileUploader; 