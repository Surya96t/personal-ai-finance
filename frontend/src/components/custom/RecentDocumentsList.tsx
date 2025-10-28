// frontend/src/components/custom/RecentDocumentsList.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { supabase } from '@/lib/supabase';
import { type RealtimePostgresChangesPayload } from '@supabase/supabase-js'; 
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from '../ui/empty';
import { CircleDashed, FileText, FileUp } from 'lucide-react';
import { Item, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle } from '../ui/item';


// --- UPDATED TYPE: Includes all new granular statuses ---
type Document = {
  id: string;
  file_name: string;
  status:
    | 'UPLOADED'
    | 'PROCESSING_OCR'
    | 'PROCESSING_ISOLATION'
    | 'PROCESSING_STRUCTURING'
    | 'PROCESSING_ENRICHMENT'
    | 'COMPLETED'
    | 'FAILED'
    // Include the old status for backward compatibility if needed
    | 'PROCESSING';
  created_at: string;
};

// --- UPGRADED HELPER COMPONENT: Recognizes new statuses and formats text ---
function StatusBadge({ status }: { status: Document['status'] }) {
  // This function determines the color and text for each status
  const getStatusProps = (
    status: Document['status']
  ): { text: string; className: string } => {
    // Make the status text more readable
    const formattedText = status.replace(/_/g, ' ').toUpperCase();

    if (status.startsWith('PROCESSING')) {
      // All "PROCESSING_..." statuses will be blue and pulsing
      const stage = status.replace('PROCESSING_', '');
      return {
        text: `PROCESSING (${stage})`,
        className: 'bg-blue-500 hover:bg-blue-500 animate-pulse',
      };
    }

    switch (status) {
      case 'COMPLETED':
        return { text: 'COMPLETED', className: 'bg-green-500 hover:bg-green-500' };
      case 'FAILED':
        return { text: 'FAILED', className: 'bg-red-500 hover:bg-red-500' };
      case 'UPLOADED':
        return { text: 'UPLOADED', className: 'bg-gray-500 hover:bg-gray-500' };
      default:
        return { text: formattedText, className: 'bg-gray-500 hover:bg-gray-500' };
    }
  };

  const { text, className } = getStatusProps(status);

  return <Badge className={`text-white ${className}`}>{text}</Badge>;
}

// The main component logic is unchanged.
export function RecentDocumentsList() {
  const { getToken } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Real-time subscription useEffect (unchanged)
  useEffect(() => {
    const handleDbChange = (payload: RealtimePostgresChangesPayload<Document>) => {
      console.log('Real-time change received!', payload);
      const newDocument = payload.new as Document;

      setDocuments((currentDocuments) => {
        if (payload.eventType === 'INSERT') {
          if (currentDocuments.some((doc) => doc.id === newDocument.id)) {
            return currentDocuments;
          }
          return [newDocument, ...currentDocuments];
        }
        if (payload.eventType === 'UPDATE') {
          return currentDocuments.map((doc) =>
            doc.id === newDocument.id ? newDocument : doc
          );
        }
        return currentDocuments;
      });
    };

    const channel = supabase
      .channel('documents-list-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'documents' },
        handleDbChange
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);


  // --- THIS useEffect handles the INITIAL data load ---
  useEffect(() => {
    const fetchDocuments = async () => {
      setIsLoading(true);
      try {
        const token = await getToken();
        const response = await fetch('http://127.0.0.1:8000/api/v1/documents', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to fetch documents.');
        const data = await response.json();
        setDocuments(data);
      } catch (error) {
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDocuments();
  }, [getToken]);

  // --- The rendered JSX is unchanged ---
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Documents</CardTitle>
        <CardDescription>The status of your most recent uploads.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && documents.length === 0 ? (
          <div className="text-center text-muted-foreground">
            <CircleDashed className="mx-auto h-8 w-8 animate-spin" />
            <p className="mt-2">Loading documents...</p>
          </div>
        ) : documents.length === 0 ? (
          // --- NEW: Using the Empty component ---
          <Empty>
            <EmptyMedia><FileUp /></EmptyMedia>
            <EmptyTitle>No Documents Yet</EmptyTitle>
            <EmptyDescription>
              Upload your first document to get started.
            </EmptyDescription>
          </Empty>
        ) : (
          // --- NEW: Using ItemGroup for the list ---
          <ItemGroup>
            {documents.map((doc) => (
              <Item key={doc.id}>
                <ItemMedia variant="icon"><FileText /></ItemMedia>
                <ItemContent>
                  <ItemTitle>{doc.file_name}</ItemTitle>
                  <ItemDescription>
                    Uploaded on {format(new Date(doc.created_at), 'LLL dd, y')}
                  </ItemDescription>
                </ItemContent>
                <StatusBadge status={doc.status} />
              </Item>
            ))}
          </ItemGroup>
        )}
      </CardContent>
    </Card>
  );
}