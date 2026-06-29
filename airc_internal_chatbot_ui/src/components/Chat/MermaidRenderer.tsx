'use client';

import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { 
  ZoomInOutlined, 
  ZoomOutOutlined, 
  CloseOutlined, 
  UndoOutlined, 
  FullscreenOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import { message } from 'antd';

// Khoi tao cau hinh mac dinh cho Mermaid o phia Client
if (typeof window !== 'undefined') {
  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
      useWidth: true as any,
    }
  });
}

let idCounter = 0;

interface MermaidRendererProps {
  code: string;
}

export default function MermaidRenderer({ code }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState<boolean>(false);

  // Trang thai cho Modal phong to va cac thao tac Zoom & Pan
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [scale, setScale] = useState<number>(1);
  const [position, setPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStart = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Dam bao chi chay tren Client de trang loi Hydration
  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;

    let active = true;
    // Tao ID duy nhat cho moi do thi Mermaid de tranh xung dot ID tren DOM
    const uniqueId = `mermaid-${++idCounter}`;

    const renderChart = async () => {
      try {
        setError(null);
        
        // Kiem tra cu phap cua doan ma Mermaid truoc khi tien hanh ve
        const isValid = await mermaid.parse(code);
        if (isValid && active) {
          const { svg: renderedSvg } = await mermaid.render(uniqueId, code);
          if (active) {
            setSvg(renderedSvg);
          }
        }
      } catch (err: any) {
        console.error('Mermaid render error:', err);
        if (active) {
          setError(err.message || 'Loi cu phap so do Mermaid.');
        }
      }
    };

    renderChart();

    return () => {
      active = false;
    };
  }, [code, isMounted]);

  // Cac ham xu ly tuong tac Pan & Zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = 0.1;
    let newScale = scale;
    if (e.deltaY < 0) {
      newScale = Math.min(scale + zoomFactor, 5); // Phong to toi da 5x
    } else {
      newScale = Math.max(scale - zoomFactor, 0.25); // Thu nho toi thieu 0.25x
    }
    setScale(newScale);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Chi cho phep chuot trai keo tha
    setIsDragging(true);
    dragStart.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
  };

  const openModal = () => {
    setIsModalOpen(true);
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  const handleReset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleDownload = () => {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(svg, 'image/svg+xml');
      const svgElement = doc.documentElement as unknown as SVGSVGElement;
      
      let width = 800;
      let height = 600;
      
      if (svgElement.viewBox && svgElement.viewBox.baseVal) {
        width = svgElement.viewBox.baseVal.width || width;
        height = svgElement.viewBox.baseVal.height || height;
      } else {
        const wAttr = svgElement.getAttribute('width');
        const hAttr = svgElement.getAttribute('height');
        if (wAttr) width = parseFloat(wAttr);
        if (hAttr) height = parseFloat(hAttr);
      }

      const canvas = document.createElement('canvas');
      canvas.width = width * 2;
      canvas.height = height * 2;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      const img = new Image();
      const svgString = new XMLSerializer().serializeToString(svgElement);
      const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(svgBlob);
      
      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const pngUrl = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.href = pngUrl;
        link.download = `so-do-mermaid-${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        message.success('Đã tải xuống ảnh sơ đồ dạng PNG!');
      };
      img.src = url;
    } catch (err) {
      console.error('Failed to download image:', err);
      message.error('Lỗi khi tải xuống ảnh sơ đồ');
    }
  };

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.2, 5));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.2, 0.25));
  };

  if (!isMounted) {
    return (
      <div className="flex items-center justify-center p-6 bg-gray-50 rounded-lg text-gray-400 text-sm border my-2 font-mono">
        Đang chuẩn bị sơ đồ...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm font-mono my-2 border border-red-200">
        <div className="font-bold mb-1">⚠️ Lỗi render sơ đồ Mermaid:</div>
        <pre className="whitespace-pre-wrap text-xs">{error}</pre>
        <pre className="mt-2 p-2 bg-red-100 rounded text-xs overflow-x-auto max-w-full">{code}</pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="flex items-center justify-center p-6 bg-gray-50 rounded-lg text-gray-400 text-sm animate-pulse border my-2 font-mono">
        Đang vẽ sơ đồ Mermaid...
      </div>
    );
  }

  return (
    <>
      {/* Vùng hiển thị sơ đồ thu nhỏ ở tin nhắn */}
      <div className="relative group my-4 max-w-full">
        <div
          ref={containerRef}
          onClick={openModal}
          className="mermaid-chart overflow-x-auto p-5 bg-white border border-gray-200 rounded-xl shadow-sm flex justify-center max-w-full cursor-zoom-in transition-all duration-200 hover:border-red-300 hover:shadow-md relative"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
        <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDownload();
            }}
            className="bg-gray-800/80 hover:bg-gray-800 text-white text-xs px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 backdrop-blur-sm shadow-sm font-sans border-none cursor-pointer"
            title="Tải xuống ảnh sơ đồ"
          >
            <DownloadOutlined className="text-sm" /> Tải ảnh
          </button>
          <span className="bg-gray-800/80 text-white text-xs px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 backdrop-blur-sm shadow-sm font-sans pointer-events-none">
            <FullscreenOutlined className="text-sm" /> Click để phóng to
          </span>
        </div>
      </div>

      {/* Modal phóng to sơ đồ */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 md:p-6" onClick={closeModal}>
          <div 
            className="w-full max-w-5xl h-[85vh] bg-white rounded-2xl shadow-2xl overflow-hidden relative flex flex-col animate-in fade-in zoom-in-95 duration-200 border border-gray-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Nút đóng (X) nổi ở góc trên bên phải */}
            <button 
              onClick={closeModal}
              className="absolute top-4 right-6 z-20 w-10 h-10 rounded-full bg-white/85 hover:bg-white border border-gray-200/80 shadow-md backdrop-blur-md flex items-center justify-center text-gray-500 hover:text-gray-800 hover:scale-105 transition-all duration-150"
              title="Đóng"
            >
              <CloseOutlined className="text-base" />
            </button>

            {/* Vùng tương tác Pan & Zoom chiếm trọn vẹn chiều cao container */}
            <div 
              className="w-full h-full relative overflow-hidden bg-slate-50 cursor-grab active:cursor-grabbing select-none flex items-center justify-center"
              onWheel={handleWheel}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseLeave}
            >
              {/* Container chứa SVG được áp dụng CSS transform */}
              <div
                style={{
                  transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.15s ease-out',
                }}
                className="w-full h-full flex items-center justify-center p-8 [&>svg]:max-w-none [&>svg]:max-h-none [&>svg]:h-auto [&>svg]:pointer-events-none pointer-events-none select-none"
                dangerouslySetInnerHTML={{ __html: svg }}
              />

              {/* Floating Control Panel ở góc dưới bên phải */}
              <div className="absolute bottom-4 right-6 z-20 flex items-center bg-white/85 hover:bg-white border border-gray-200/80 backdrop-blur-md px-3.5 py-1.5 rounded-xl shadow-md transition-colors duration-150">
                {/* Info trạng thái Zoom */}
                <span className="text-xs font-semibold text-gray-500 mr-2 border-r border-gray-200 pr-3 select-none font-sans">
                  Tỷ lệ: {Math.round(scale * 100)}%
                </span>

                {/* Nút điều khiển */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleZoomOut}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-gray-800 hover:bg-gray-100/80 transition-all duration-150"
                    title="Thu nhỏ"
                  >
                    <ZoomOutOutlined className="text-base" />
                  </button>
                  <button
                    onClick={handleZoomIn}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-gray-800 hover:bg-gray-100/80 transition-all duration-150"
                    title="Phóng to"
                  >
                    <ZoomInOutlined className="text-base" />
                  </button>
                  <button
                    onClick={handleReset}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-gray-800 hover:bg-gray-100/80 transition-all duration-150"
                    title="Đặt lại vị trí"
                  >
                    <UndoOutlined className="text-base" />
                  </button>
                  <button
                    onClick={handleDownload}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-gray-800 hover:bg-gray-100/80 transition-all duration-150 border-l border-gray-200 pl-1 ml-1"
                    title="Tải xuống ảnh sơ đồ"
                  >
                    <DownloadOutlined className="text-base" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
