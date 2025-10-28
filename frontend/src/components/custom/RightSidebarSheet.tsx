// frontend/src/components/custom/RightSidebarSheet.tsx
'use client';

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { DocumentUploadModal } from "./DocumentUploadModal"; // <-- Import the new modal
import { RecentDocumentsList } from "./RecentDocumentsList";
import { FileUp, PlusCircle } from "lucide-react";

export function RightSidebarSheet() {
  // State to control the modal's visibility
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline">
            <FileUp className="mr-2 h-4 w-4" />
            Manage Documents
          </Button>
        </SheetTrigger>
        <SheetContent className="w-full sm:max-w-xl p-0">
          <div className="h-full flex flex-col">
            <SheetHeader className="p-6">
              <SheetTitle>Document Center</SheetTitle>
              <SheetDescription>
                Upload new statements or view the status of recent ones.
              </SheetDescription>
            </SheetHeader>
            <div className="p-6 border-b">
              {/* This button now opens the modal */}
              <Button className="w-full" onClick={() => setIsModalOpen(true)}>
                <PlusCircle className="mr-2 h-4 w-4" />
                Upload a New Document
              </Button>
            </div>
            <div className="flex-grow p-6 space-y-8 overflow-y-auto">
              <RecentDocumentsList />
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* The Modal itself, controlled by the button above */}
      <DocumentUploadModal isOpen={isModalOpen} onOpenChange={setIsModalOpen} />
    </>
  );
}