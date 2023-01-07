{
  description = "blender plugin";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "nixpkgs/nixos-unstable";
    objset.url = "github:waelwindows/objset";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    objset,
  }: let
  in
    flake-utils.lib.eachDefaultSystem (
      system: let
        overlays = [objset.overlays.default];
        pkgs = import nixpkgs {inherit system overlays;};
      in rec {
        devShells.default = pkgs.mkShell rec {
          # Set PYTHONPATH to make blender load `objset`
          PYTHONPATH="${objset.packages.${system}.objset-python}/lib/python3.10/site-packages:";
          buildInputs = with pkgs; [
            python-language-server
            blender
          ];
        };
      }
    );
}
