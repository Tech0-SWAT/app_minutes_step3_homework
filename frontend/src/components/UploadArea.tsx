"use client";
import React from 'react';
import { UploadIcon } from './UploadIcon';
import { SmallUploadIcon } from './SmallUploadIcon';

export const UploadArea: React.FC = () => {
  return (
    <section className="flex gap-1 justify-center items-start px-6 py-5 w-full h-[735px] max-sm:px-4 max-sm:h-auto max-sm:min-h-[600px]">
      <div className="flex flex-col flex-1 justify-center items-center h-[695px] max-w-[960px] max-sm:h-auto">
        <div className="flex flex-col items-center px-4 w-full">
          <div>
            <UploadIcon className="w-[74px] h-[74px] mb-[20px] max-sm:w-[60px] max-sm:h-[60px]" />
          </div>
          <div>
            <SmallUploadIcon className="w-[24px] h-[24px] mb-[20px] max-sm:w-[20px] max-sm:h-[20px]" />
          </div>
        </div>
        <h2 className="px-4 py-5 text-2xl font-bold leading-7 text-center text-neutral-900 max-sm:px-3 max-sm:py-4 max-sm:w-full max-sm:text-lg max-sm:leading-6">
          動画をアップロードしてください
        </h2>
        <button className="gap-2.5 px-5 py-2 text-2xl font-bold leading-7 text-center text-white bg-sky-500 rounded-3xl duration-200 cursor-pointer max-sm:px-4 max-sm:py-2.5 max-sm:text-lg max-sm:leading-6">
          選択
        </button>
      </div>
    </section>
  );
};
