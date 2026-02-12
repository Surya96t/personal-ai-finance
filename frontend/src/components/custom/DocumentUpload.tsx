// frontend/src/components/custom/DocumentUpload.tsx
'use client';

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner"

// --- NEW HELPER FUNCTION: Calculates the SHA-256 hash of a file ---
async function calculateFileHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

export function DocumentUpload() {
  const { getToken } = useAuth();
  const [isUploading, setIsUploading] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    toast("Starting upload...");

    try {
      // --- NEW: Calculate file hash before anything else ---
      toast("Calculating file fingerprint...");
      const fileHash = await calculateFileHash(file);
      console.log("File hash:", fileHash);

      // === STEP 1: Get secure upload URL (unchanged) ===
      const token = await getToken();
      const responseStep1 = await fetch("http://127.0.0.1:8000/api/v1/documents/generate-upload-url", {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!responseStep1.ok) throw new Error("Failed to get upload URL.");
      const { upload_url, path, token: uploadToken } = await responseStep1.json();
      console.log("Received upload URL:", upload_url);

      // === STEP 2: Upload the file directly to Supabase Storage ===
      // Supabase Signed Upload URLs require the token in the Authorization header
      const headers: HeadersInit = {
        'Content-Type': file.type,
      };
      if (uploadToken) {
        headers['Authorization'] = `Bearer ${uploadToken}`;
      }

      const responseStep2 = await fetch(upload_url, {
        method: 'PUT',
        headers: headers,
        body: file,
      });

      if (!responseStep2.ok) throw new Error("Failed to upload file to storage.");
      toast.success("File uploaded successfully! Processing will begin shortly.");

      // === STEP 3: Notify backend, NOW INCLUDING THE HASH ===
      const responseStep3 = await fetch("http://127.0.0.1:8000/api/v1/documents/process", {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          file_name: file.name, 
          storage_path: path, // Changed from gcs_path to storage_path
          file_hash: fileHash, 
        }),
      });

      // --- NEW: Handle the 409 Conflict error for duplicates ---
      if (responseStep3.status === 409) {
        toast.error("Duplicate Document", {
          description: "This exact file has already been uploaded.",
        });
        return; // Stop the process
      }
      
      if (!responseStep3.ok) throw new Error("Failed to start processing.");
      
      const result = await responseStep3.json();
      toast.info("Document is now in the processing queue.");

    } catch (error) {
      console.error("Upload process failed:", error);
      toast.error(`Error: ${(error as Error).message}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload a Document</CardTitle>
        <CardDescription>Upload a bank or credit card statement to begin.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid w-full max-w-sm items-center gap-1.5">
          <Label htmlFor="statement">Financial Statement</Label>
          <Input id="statement" type="file" onChange={handleFileUpload} disabled={isUploading} accept=".pdf,.jpg,.png" />
          {isUploading && <p className="text-sm text-slate-500 mt-2">Uploading, please wait...</p>}
        </div>
      </CardContent>
    </Card>
  );
}