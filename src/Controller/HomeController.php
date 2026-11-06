<?php

namespace App\Controller;

use App\Repository\AlbumRepository;
use App\Repository\MediaRepository;
use App\Repository\UserRepository;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\Routing\Annotation\Route;

class HomeController extends AbstractController
{
    #[Route("/", name: "home")]
    public function home()
    {
        return $this->render('front/home.html.twig');
    }

    #[Route("/guests", name: "guests")]
    public function guests(UserRepository $users)
    {
        $guests = $users->findBy(['admin' => false]);
        return $this->render('front/guests.html.twig', [
            'guests' => $guests
        ]);
    }

    #[Route("/guest/{id}", name: "guest")]
    public function guest(int $id, UserRepository $users)
    {
        $guest = $users->find($id);
        return $this->render('front/guest.html.twig', [
            'guest' => $guest
        ]);
    }

    #[Route("/portfolio/{id}", name: "portfolio")]
    public function portfolio(AlbumRepository $albumsRepository, MediaRepository $mediasRepository, UserRepository $users, ?int $id = null)
    {
        $albums = $albumsRepository->findAll();
        $album = $id ? $albumsRepository->find($id) : null;
        $user = $users->findOneByAdmin(true);

        $medias = $album
            ? $mediasRepository->findByAlbum($album)
            : $mediasRepository->findByUser($user);
        return $this->render('front/portfolio.html.twig', [
            'albums' => $albums,
            'album' => $album,
            'medias' => $medias
        ]);
    }

    #[Route("/about", name: "about")]
    public function about()
    {
        return $this->render('front/about.html.twig');
    }
}