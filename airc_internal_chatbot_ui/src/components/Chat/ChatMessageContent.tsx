'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import MermaidRenderer from './MermaidRenderer';

interface ChatMessageContentProps {
  content: string;
  isUser?: boolean;
}

export default function ChatMessageContent({ content, isUser = false }: ChatMessageContentProps) {
  // Neu la tin nhan tu nguoi dung, hien thi dang text thuan giu nguyen xuong dong
  if (isUser) {
    return <p className="m-0 whitespace-pre-wrap">{content}</p>;
  }

  // Dinh nghia cac custom component cho tung phan tu Markdown
  const markdownComponents: Components = {
    p: ({ ...props }) => <p className="mb-2 leading-relaxed" {...props} />,
    ul: ({ ...props }) => <ul className="list-disc list-outside mb-2 pl-5 space-y-1" {...props} />,
    ol: ({ ...props }) => <ol className="list-decimal list-outside mb-2 pl-5 space-y-1" {...props} />,
    li: ({ ...props }) => <li className="mb-1" {...props} />,
    h1: ({ ...props }) => <h1 className="text-xl font-bold mb-2 mt-4 text-gray-900" {...props} />,
    h2: ({ ...props }) => <h2 className="text-lg font-bold mb-2 mt-3 text-gray-800" {...props} />,
    h3: ({ ...props }) => <h3 className="text-base font-bold mb-2 mt-2 text-gray-800" {...props} />,
    strong: ({ ...props }) => <strong className="font-semibold text-gray-900" {...props} />,
    blockquote: ({ ...props }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic mb-2 text-gray-600" {...props} />,
    code: ({ className, children, ...props }) => {
      const match = /language-(\w+)/.exec(className || '');
      const isInline = !className?.includes('language-');

      // Check neu la ma nguon Mermaid thi render bang component MermaidRenderer
      if (match && match[1] === 'mermaid') {
        return <MermaidRenderer code={String(children).replace(/\n$/, '')} />;
      }

      return isInline ? (
        <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-red-600" {...props}>
          {children}
        </code>
      ) : (
        <code className={`block bg-gray-100 p-3 rounded-lg text-sm font-mono overflow-x-auto mb-2 border border-gray-200 ${className || ''}`} {...props}>
          {children}
        </code>
      );
    },
  };

  return (
    <div className="markdown-content text-gray-800">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
