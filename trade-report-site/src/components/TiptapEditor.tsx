'use client';

import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import React from 'react';

const MenuBar = ({ editor }: { editor: Editor | null }) => {
  if (!editor) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 p-2 mb-4 border border-gray-300 rounded-t-lg bg-gray-50">
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBold().run()}
        disabled={!editor.can().chain().focus().toggleBold().run()}
        className={editor.isActive('bold') ? 'is-active' : ''}
      >
        Bold
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        disabled={!editor.can().chain().focus().toggleItalic().run()}
        className={editor.isActive('italic') ? 'is-active' : ''}
      >
        Italic
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleStrike().run()}
        disabled={!editor.can().chain().focus().toggleStrike().run()}
        className={editor.isActive('strike') ? 'is-active' : ''}
      >
        Strike
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().setParagraph().run()}
        className={editor.isActive('paragraph') ? 'is-active' : ''}
      >
        Paragraph
      </button>
      {/* Add more buttons for other formatting options as needed */}
    </div>
  );
};

interface TiptapEditorProps {
  content: string;
  onChange: (richText: string) => void;
}

export const TiptapEditor = ({ content, onChange }: TiptapEditorProps) => {
  const editor = useEditor({
    extensions: [StarterKit],
    content: content,
    editorProps: {
      attributes: {
        class: 'prose max-w-none p-4 border border-gray-300 rounded-b-lg focus:outline-none min-h-[300px]',
      },
    },
    onUpdate({ editor }) {
      onChange(editor.getHTML());
    },
  });

  return (
    <div>
      <MenuBar editor={editor} />
      <EditorContent editor={editor} />
      <style jsx global>{`
        .is-active {
          background-color: #e0e0e0;
          font-weight: bold;
        }
        button {
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          border: 1px solid #ccc;
        }
        button:disabled {
          opacity: 0.5;
        }
      `}</style>
    </div>
  );
};
