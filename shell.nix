let
  sources = import ./nix/sources.nix;
  pkgs = import sources.nixpkgs {};
  inherit (pkgs) lib stdenv;
  repoRoot = toString ./.;
in
pkgs.mkShell {
  name = "rawfile-shell";
  buildInputs = with pkgs; [
    kubectl
    kubernetes-helm-wrapped
    helm-docs
    nixos-shell
    (kind.overrideAttrs(old: rec {
      version = "0.32.0";
      src = old.src.override {
        rev = "v${version}";
        hash = "sha256-ii0VhS1Nib+r2ZFIIkRvkcGY1fLxev6WnhbqvaZW7j8=";
      };
      vendorHash = "sha256-tRpylYpEGF6XqtBl7ESYlXKEEAt+Jws4x4VlUVW8SNI=";
    })) # kind 0.32.0 is not available in nixpkgs yet and we need it to be compatible with latest containerd
    git
    python313
    poetry # Python3.13 is not supported (Overriding python3 input will not work)
    gcc
    gnumake
    stdenv.cc.cc.lib
    xfsprogs
    niv
  ] ++ pkgs.lib.optional (builtins.getEnv "IN_NIX_SHELL" == "pure") docker-client
  ++ pkgs.lib.optional stdenv.isLinux pkgs.btrfs-progs;

  LD_LIBRARY_PATH = lib.makeLibraryPath [ pkgs.stdenv.cc.cc ];
  PYTHONPATH = "${repoRoot}/rawfile";

  shellHook = ''
    poetry env use "$(which python)"
    poetry install
    source $(poetry env info -p)/bin/activate
    if ! [ "$CI" == "1" ]; then
      pre-commit install
    fi
  '';
  postShellHook = ''
    deactivate
    unset PYTHONPATH
  '';
}
