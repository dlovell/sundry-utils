{
  description = "A sundry collection of tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
    flake-utils.url = "github:/numtide/flake-utils";
    nix-utils = {
      url = "github:letsql/nix-utils";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, nix-utils }: (flake-utils.lib.eachDefaultSystem (system:
  let
    pkgs = import nixpkgs { inherit system; };
    utils = nix-utils.lib.${system}.mkUtils { inherit pkgs; };
    nix-flake-metadata-refresh = utils.mkNixFlakeMetadataRefreshApp "github:dlovell/sundry-utils";
    check-pyproject-dependencies = pkgs.writeScriptBin "check-pyproject-dependencies" ''
      set -eux

      ${./scripts/check-pyproject-dependencies.py} "''${@}"
    '';
  in
  {
    programs = {
      inherit check-pyproject-dependencies;
    };
    apps = {
      inherit nix-flake-metadata-refresh;
      check-pyproject-dependencies = utils.drvToApp { drv = check-pyproject-dependencies; };
      default = self.apps.${system}.check-pyproject-dependencies;
    };
    lib = {
    };
    devShells = {
    };
  }));
}
