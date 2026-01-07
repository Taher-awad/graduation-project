import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stage, useGLTF, Html, useProgress } from '@react-three/drei';

function Loader() {
  const { progress } = useProgress();
  return <Html center className="text-white font-mono">{progress.toFixed(0)} % loaded</Html>;
}

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

export const ModelViewer = ({ url }: { url: string }) => {
  return (
    <div className="w-full h-full bg-slate-950 rounded-xl overflow-hidden relative">
      <Canvas shadows dpr={[1, 2]} camera={{ fov: 50 }}>
        <Suspense fallback={<Loader />}>
          <Stage environment="city" intensity={0.6}>
            <Model url={url} />
          </Stage>
        </Suspense>
        <OrbitControls makeDefault autoRotate />
      </Canvas>
      <div className="absolute bottom-4 right-4 text-xs text-slate-500 bg-black/50 px-2 py-1 rounded">
        Left Click: Rotate | Right Click: Pan | Scroll: Zoom
      </div>
    </div>
  );
};
