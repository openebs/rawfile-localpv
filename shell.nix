let
  sources = import ./nix/sources.nix;
  pkgs = import sources.nixpkgs {};
  unstable-pkgs = import sources.nixpkgs-unstable {};
  inherit (pkgs) lib stdenv;
in
pkgs.mkShell {
  name = "rawfile-shell";

  NIX_LD_LIBRARY_PATH = lib.makeLibraryPath [
    pkgs.stdenv.cc.cc
  ];

  buildInputs = with pkgs; [
    kubectl
    kubernetes-helm-wrapped
    helm-docs
    nixos-shell
    unstable-pkgs.kind
    python313
    poetry # Python3.13 is not supported (Overriding python3 input will not work)
    gcc
    gnumake
    btrfs-progs
    stdenv.cc.cc.lib
  ] ++ pkgs.lib.optional (builtins.getEnv "IN_NIX_SHELL" == "pure") [ docker-client ];
  NIX_LD = builtins.readFile "${stdenv.cc}/nix-support/dynamic-linker";
  shellHook = ''
    poetry env use $(which python)
    poetry install
    source $(poetry env info -p)/bin/activate
    pre-commit install
  '';
  postShellHook = ''
    deactivate
  '';
}
