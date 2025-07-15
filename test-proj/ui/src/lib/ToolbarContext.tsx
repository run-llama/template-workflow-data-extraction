import React from "react";

export const ToolbarCtx = React.createContext<{
  buttons: React.ReactNode[];
  setButtons: (fn: (prev: React.ReactNode[]) => React.ReactNode[]) => void;
}>({ buttons: [], setButtons: () => {} });

export const ToolbarProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [buttons, setButtons] = React.useState<React.ReactNode[]>([]);
  return (
    <ToolbarCtx.Provider value={{ buttons, setButtons }}>
      {children}
    </ToolbarCtx.Provider>
  );
};
export const useToolbar = () => React.useContext(ToolbarCtx);
