// frontend/src/components/custom/DocumentUploadModal.tsx
'use client';

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

// The hash function remains the same
async function calculateFileHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

interface DocumentUploadModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

export function DocumentUploadModal({ isOpen, onOpenChange }: DocumentUploadModalProps) {
  const { getToken } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Effect to create a preview URL when a file is selected
  useEffect(() => {
    if (selectedFile) {
      const url = URL.createObjectURL(selectedFile);
      setPreviewUrl(url);
      // Clean up the object URL when the component unmounts or file changes
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl(null);
  }, [selectedFile]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleConfirmUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    toast("Starting upload...");

    try {
      const fileHash = await calculateFileHash(selectedFile);
      const token = await getToken();

      const responseStep1 = await fetch("http://127.0.0.1:8000/api/v1/documents/generate-upload-url", {
        method: 'POST', headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!responseStep1.ok) throw new Error("Failed to get upload URL.");
      const { upload_url, gcs_path } = await responseStep1.json();

      const responseStep2 = await fetch(upload_url, {
        method: 'PUT', headers: { 'Content-Type': selectedFile.type }, body: selectedFile
      });
      if (!responseStep2.ok) throw new Error("Failed to upload file to storage.");

      const responseStep3 = await fetch("http://127.0.0.1:8000/api/v1/documents/process", {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_name: selectedFile.name, gcs_path, file_hash: fileHash }),
      });

      if (responseStep3.status === 409) {
        toast.error("Duplicate Document", { description: "This exact file has already been uploaded." });
        return;
      }
      if (!responseStep3.ok) throw new Error("Failed to start processing.");
      
      toast.success("Processing Queued!", { description: `Your document (${selectedFile.name}) is in the queue.` });
    } catch (error) {
      toast.error("Upload Failed", { description: (error as Error).message });
    } finally {
      setIsUploading(false);
      onOpenChange(false);
      setSelectedFile(null);
    }
  };
  
  // Reset state when the modal is closed
  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setSelectedFile(null);
      setPreviewUrl(null);
      setIsUploading(false);
    }
    onOpenChange(open);
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      {/* --- THIS IS THE MODIFIED LINE --- */}
      <DialogContent className="max-w-5xl h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Upload New Document</DialogTitle>
          <DialogDescription>Select a file to preview it before uploading.</DialogDescription>
        </DialogHeader>
        
        {/* The "flex-grow" class makes this div fill the available space */}
        <div className="grid md:grid-cols-2 gap-6 flex-grow overflow-hidden">
          
          {/* Left Column: Upload */}
          <div className="flex flex-col gap-4 p-4 border-r">
            <Label htmlFor="statement-upload" className="text-lg font-semibold">Choose File</Label>
            <Input id="statement-upload" type="file" onChange={handleFileSelect} accept=".pdf,.jpg,.png" />
            {selectedFile && (
              <div className="text-sm text-muted-foreground mt-2 space-y-1">
                <p><strong>Filename:</strong> {selectedFile.name}</p>
                <p><strong>Size:</strong> {(selectedFile.size / 1024).toFixed(2)} KB</p>
              </div>
            )}
          </div>

          {/* Right Column: Preview */}
          <div className="border rounded-md bg-muted/20 h-full flex flex-col">
             <div className="p-4 border-b font-semibold">Preview</div>
             {previewUrl ? (
              <iframe src={`${previewUrl}#view=FitH`} className="w-full flex-grow" title="File Preview" />
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <p>Select a file to see a preview</p>
              </div>
            )}
          </div>
        </div>
        
        <DialogFooter className="pt-4 border-t">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleConfirmUpload} disabled={!selectedFile || isUploading}>
            {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Confirm & Upload
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}