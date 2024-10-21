import React, { useState } from 'react';
import Markdown from 'markdown-to-jsx';

const CodeEditor = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);

    const reader = new FileReader();
    reader.onload = (e) => setFileContent(e.target.result);
    reader.readAsText(file);
  };

  return (
    <div>
      <input type="file" onChange={handleFileChange} />
      {selectedFile && <h3>{selectedFile.name}</h3>}
      <Markdown>{fileContent}</Markdown>
    </div>
  );
};

export default CodeEditor;